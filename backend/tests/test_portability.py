import json
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, select, text

from app.db import Base
from app.models import Document, User
from app.services.migration import MigrationConflict, transfer
from tests.conftest import account, pdf_fixture


def test_export_owner_and_no_credentials(client, user, vacancy):
    client.post("/api/jobs", json=vacancy)
    client.post(
        "/api/documents/upload", files={"file": ("fixture.pdf", pdf_fixture(), "application/pdf")}
    )
    first = client.get("/api/export")
    assert first.status_code == 200
    with ZipFile(BytesIO(first.content)) as archive:
        names = archive.namelist()
        assert "timeline.json" in names
        assert any(n.endswith(".pdf") for n in names)
        assert not any("session" in n or "usage" in n for n in names)
        data = archive.read("manifest.json") + archive.read("profile.json")
        assert b"password_hash" not in data and b"csrf_token" not in data
        assert len(json.loads(archive.read("jobs.json"))) == 1
    account(client, "export-other@example.com")
    with ZipFile(BytesIO(client.get("/api/export").content)) as archive:
        assert json.loads(archive.read("jobs.json")) == []
        assert json.loads(archive.read("documents.json")) == []


def test_resume_selection_exports_and_stale_version(client, user, vacancy):
    profile = client.get("/api/profile").json()
    profile["data"]["experiences"] = [
        {"title": "Python real", "organization": "Original", "description": "Pipeline comprovado"},
        {"title": "Outro cargo", "organization": "Outra"},
    ]
    profile = client.put(
        "/api/profile", json={"version": profile["version"], "data": profile["data"]}
    ).json()
    job = client.post("/api/jobs", json=vacancy).json()
    app = client.get(f"/api/jobs/{job['id']}").json()["application"]
    payload = {"profile_version": profile["version"], "experiences": [0], "projects": []}
    preview = client.post(f"/api/applications/{app['id']}/resume-preview", json=payload)
    assert preview.status_code == 200
    assert "Python real" in preview.json()["text"] and "Outro cargo" not in preview.json()["text"]
    doc = client.post(f"/api/applications/{app['id']}/resume", json=payload).json()
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 409
    docx = client.get(f"/api/documents/{doc['id']}/download?format=docx")
    with ZipFile(BytesIO(docx.content)) as archive:
        for name in archive.namelist():
            if name.endswith("xml") or name.endswith("rels"):
                ElementTree.fromstring(archive.read(name))
        assert "Python real" in archive.read("word/document.xml").decode()
    html = client.get(f"/api/documents/{doc['id']}/download?format=html")
    assert "Python real" in html.text
    payload["profile_version"] += 1
    assert (
        client.post(f"/api/applications/{app['id']}/resume-preview", json=payload).status_code
        == 409
    )


def test_transfer_dry_run_repeat_and_conflict(database, user, tmp_path):
    source = database.kw["bind"]
    target = create_engine("sqlite:///" + str(tmp_path / "target.db"))
    Base.metadata.create_all(target)
    for engine in (source, target):
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('test')"))
    with database() as db:
        parent = Document(user_id=user["id"], name="Original", text="Fatos", content=pdf_fixture())
        db.add(parent)
        db.flush()
        db.add(Document(user_id=user["id"], name="Derivado", text="Fatos", parent_id=parent.id))
        db.commit()
    report = transfer(source, target, False)
    assert report["documents"]["new"] == 2
    with target.connect() as conn:
        assert conn.execute(select(User)).all() == []
    transfer(source, target, True)
    report = transfer(source, target, True)
    assert report["documents"]["identical"] == 2
    with target.begin() as conn:
        conn.execute(User.__table__.update().values(name="Conflito"))
    with pytest.raises(MigrationConflict):
        transfer(source, target, True)
    target.dispose()


def test_diagnostics_contains_no_connection_secrets(client, user):
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    for secret in ("database_url", "api_key", "password_hash", "csrf_token"):
        assert secret not in response.text


def test_health_rejects_old_schema(client, database, monkeypatch):
    import app.main as main
    from app.services.health import expected_revision

    monkeypatch.setattr(main, "SessionLocal", database)
    with database() as db:
        db.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        db.execute(text("INSERT INTO alembic_version VALUES ('old')"))
        db.commit()
    assert client.get("/api/health").status_code == 503
    with database() as db:
        db.execute(
            text("UPDATE alembic_version SET version_num=:head"), {"head": expected_revision()}
        )
        db.commit()
    assert client.get("/api/health").status_code == 200


def test_html_escapes_untrusted_document_content():
    from app.services.document_formats import resume_html

    rendered = resume_html('<script>alert("x")</script>\nText & facts').decode()
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_production_preflight_is_secret_free():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "check_production.py"
    spec = importlib.util.spec_from_file_location("production_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    env = {
        "ENVIRONMENT": "production",
        "COOKIE_SECURE": "true",
        "APP_ORIGIN": "https://career.example.com",
        "ALLOWED_ORIGINS": "https://career.example.com",
        "DATABASE_URL": "postgresql+psycopg://private-connection",
        "REGISTRATION_ENABLED": "false",
    }
    config = {
        "services": {
            "api": {"environment": env},
            "worker": {"environment": dict(env)},
            "db": {"environment": {"POSTGRES_PASSWORD": "FixturePasswordWith24Letters123"}},
            "caddy": {
                "environment": {"DOMAIN": "career.example.com", "ACME_EMAIL": "fixture@example.com"}
            },
        }
    }
    assert module.check(config) == []
    config["services"]["api"]["environment"]["COOKIE_SECURE"] = "false"
    errors = module.check(config)
    assert errors and "private-connection" not in str(errors)
