from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.models import ApplicationEvent, FollowUp, Task, now
from tests.conftest import account, pdf_fixture


def save_job(client, vacancy):
    response = client.post("/api/jobs", json=vacancy)
    assert response.status_code == 201, response.text
    return client.get("/api/jobs/" + response.json()["id"]).json()


def test_auth_csrf_and_logout(client, user):
    assert client.get("/api/auth/me").json()["email"] == user["email"]
    assert client.get("/api/jobs").status_code == 200
    token = client.headers.pop("X-CSRF-Token")
    assert client.post("/api/profile/skills", json={"name": "SQL"}).status_code == 403
    client.headers["X-CSRF-Token"] = token
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/jobs").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": user["email"], "password": "testing-password-123!"}
        ).status_code
        == 200
    )


def test_first_account_limit_sqlite(client, monkeypatch):
    monkeypatch.setattr(settings(), "registration_limit", 1)
    assert client.get("/api/auth/config").json()["registration_open"]
    account(client)
    assert not client.get("/api/auth/config").json()["registration_open"]
    result = client.post(
        "/api/auth/register",
        json={
            "name": "Outra conta",
            "email": "second@example.com",
            "password": "testing-password-456!",
        },
    )
    assert result.status_code == 403


def test_tenant_isolation_every_domain(client, user, vacancy):
    job = save_job(client, vacancy)
    skill = client.post("/api/profile/skills", json={"name": "SQL"}).json()
    doc = client.post(
        "/api/documents", json={"name": "Privado", "text": "Meus dados privados"}
    ).json()
    with TestClient(app) as other:
        account(other, "other@example.com")
        assert other.get("/api/jobs").json()["total"] == 0
        assert other.get("/api/search?q=Empresa").json()["jobs"] == []
        assert other.get(f"/api/jobs/{job['id']}").status_code == 404
        assert other.get(f"/api/analyses/{job['analysis']['id']}").status_code == 404
        assert other.get(f"/api/documents/{doc['id']}/download").status_code == 404
        assert other.delete(f"/api/profile/skills/{skill['id']}").status_code == 404
        assert (
            other.post(
                f"/api/applications/{job['application']['id']}/notes", json={"body": "test"}
            ).status_code
            == 404
        )


def test_profile_versioning_and_recalculation(client, user, vacancy):
    job = save_job(client, vacancy)
    p = client.get("/api/profile").json()
    p["data"]["desired_roles"] = ["Engenheiro de Dados"]
    update = {"data": p["data"], "version": p["version"]}
    assert client.put("/api/profile", json=update).status_code == 200
    assert client.put("/api/profile", json=update).status_code == 409
    assert client.get(f"/api/jobs/{job['id']}").json()["analysis_stale"]
    assert client.post(f"/api/jobs/{job['id']}/analyze").status_code == 200
    assert not client.get(f"/api/jobs/{job['id']}").json()["analysis_stale"]


def test_pipeline_followups_history_and_conflict(client, user, vacancy, database):
    job = save_job(client, vacancy)
    application = job["application"]
    endpoint = f"/api/applications/{application['id']}/status"
    body = {"status": "applied", "version": 1}
    assert client.patch(endpoint, json=body).status_code == 200
    assert client.patch(endpoint, json=body).status_code == 409
    detail = client.get(f"/api/jobs/{job['id']}").json()
    assert detail["application"]["status"] == "applied"
    assert len([e for e in detail["events"] if e["kind"] == "status_changed"]) == 1
    assert detail["followups"][0]["status"] == "pending"
    with database() as db:
        follow = db.scalar(select(FollowUp))
        assert now() + timedelta(days=6) < follow.due_at < now() + timedelta(days=8)
        follow.due_at = now() - timedelta(days=1)
        db.commit()
    assert len(client.get("/api/dashboard").json()["followups"]) == 1
    assert len(client.get("/api/notifications").json()) == 1
    assert len(client.get("/api/notifications").json()) == 1
    assert (
        client.patch(
            endpoint,
            json={"status": "rejected", "version": 2, "rejection_reason": "Vaga encerrada"},
        ).status_code
        == 200
    )
    assert not client.get("/api/dashboard").json()["followups"]
    assert client.get("/api/analytics").json()["rejection_reasons"] == {"Vaga encerrada": 1}
    with database() as db:
        assert (
            len(
                db.scalars(
                    select(ApplicationEvent).where(ApplicationEvent.kind == "status_changed")
                ).all()
            )
            == 2
        )


def test_dedup_filters_and_pagination(client, user, vacancy):
    job = save_job(client, vacancy)
    again = client.post("/api/jobs", json=vacancy).json()
    assert not again["created"] and again["id"] == job["id"]
    save_job(
        client,
        {**vacancy, "title": "Analista de Dados", "url": "https://example.org/role?utm_source=a"},
    )
    again = client.post(
        "/api/jobs",
        json={**vacancy, "title": "Outro título", "url": "https://example.org/role?utm_source=b"},
    ).json()
    assert not again["created"]
    result = client.get("/api/jobs?per_page=1").json()
    assert result["total"] == 2 and len(result["items"]) == 1
    assert client.get("/api/jobs?q=Analista").json()["total"] == 1
    assert client.get("/api/jobs?skill=Python%203").json()["total"] == 2
    assert client.get("/api/jobs?work_model=onsite").json()["total"] == 0


def test_gaps_evidence_and_real_percentages(client, user, vacancy):
    p = client.get("/api/profile").json()
    p["data"].update(
        desired_roles=["Engenheiro de Dados"], seniority="junior", work_models=["remote"]
    )
    assert (
        client.put("/api/profile", json={"data": p["data"], "version": p["version"]}).status_code
        == 200
    )
    for name in ("Python", "SQL"):
        skill = client.post("/api/profile/skills", json={"name": name, "level": 3}).json()
        client.post(
            f"/api/profile/skills/{skill['id']}/evidence",
            json={
                "kind": "project",
                "title": "Pipeline real",
                "description": "Implementei um pipeline para analisar dados públicos.",
            },
        )
    job = save_job(client, vacancy)
    assert job["analysis"]["result"]["score"] > 60
    result = client.get("/api/gaps").json()
    assert result["sample_size"] == 1
    aws = next(s for s in result["skills"] if s["skill"] == "aws")
    assert aws["percentage"] == 100 and aws["count"] == 1 and aws["category"] == "missing"


def test_document_upload_and_real_workflow(client, user, vacancy):
    upload = client.post(
        "/api/documents/upload", files={"file": ("resume.pdf", pdf_fixture(), "application/pdf")}
    )
    assert upload.status_code == 201, upload.text
    doc = upload.json()
    assert "Test Candidate" in doc["text"] and doc["extracted"]["skills"]
    assert client.get(f"/api/documents/{doc['id']}/download").content.startswith(b"%PDF-")
    assert (
        client.post(
            "/api/documents/upload", files={"file": ("evil.pdf", b"not a pdf", "application/pdf")}
        ).status_code
        == 422
    )
    job = save_job(client, vacancy)
    root = "/api/applications/" + job["application"]["id"]
    assert client.post(root + "/resume/" + doc["id"]).status_code == 200
    message = client.post(root + "/messages", json={"kind": "first_contact"}).json()
    assert vacancy["company"] in message["body"]
    assert (
        client.put(
            f"/api/messages/{message['id']}", json={"body": "Mensagem revisada com fatos reais."}
        ).status_code
        == 200
    )
    assert client.post(f"/api/messages/{message['id']}/sent").status_code == 200
    assert (
        client.put(f"/api/messages/{message['id']}", json={"body": "Alteração tardia"}).status_code
        == 409
    )
    interview = client.post(
        root + "/interviews",
        json={
            "title": "Entrevista técnica",
            "kind": "technical",
            "scheduled_at": (now() + timedelta(days=1)).isoformat() + "Z",
        },
    ).json()
    preparation = client.post(f"/api/interviews/{interview['id']}/prepare").json()
    assert vacancy["title"] in preparation["preparation"]["body"]
    assert "STAR" in preparation["preparation"]["body"]
    assert client.get("/api/analytics").json()["interview_count"] == 1


def test_origin_and_ai_unavailable_are_explicit(client, user):
    assert (
        client.post(
            "/api/profile/skills",
            headers={"Origin": "https://evil.example"},
            json={"name": "Python"},
        ).status_code
        == 403
    )
    assert client.post("/api/coach", json={"body": "Qual meu próximo passo?"}).status_code == 503
    assert client.get("/api/coach/conversations").json() == []
    assert client.get("/api/ai/status").json()["configured"] is False


def test_url_import_blocks_arbitrary_fetches(client, user):
    for url in (
        "http://127.0.0.1/admin",
        "https://169.254.169.254/metadata",
        "https://evil.example/jobs",
        "https://github.com/x/y",
    ):
        assert client.post("/api/jobs/from-url", json={"url": url}).status_code == 422


def test_worker_recalculates_persisted_tasks(client, user, vacancy, database, monkeypatch):
    from app import worker

    monkeypatch.setattr(worker, "SessionLocal", database)
    job = save_job(client, vacancy)
    client.post("/api/profile/skills", json={"name": "Python"})
    assert worker.run_once()
    assert client.get(f"/api/jobs/{job['id']}").json()["score"] is not None
    with database() as db:
        assert db.scalar(select(Task)).status == "completed"


def test_ai_schema_cache_and_untrusted_citations(client, user, monkeypatch):
    from app.ai.provider import Advice, Citation, OpenAIProvider

    monkeypatch.setattr(settings(), "openai_api_key", "test-only-key")
    p = client.get("/api/profile").json()
    p["data"]["ai_consent"] = True
    client.put("/api/profile", json={"data": p["data"], "version": p["version"]})
    calls = []

    def fake(self, instruction, context, schema):
        calls.append(context)
        return Advice(
            body="Revise os objetivos do seu perfil.",
            citations=[Citation(source_id="profile", quote="Candidato de teste")],
            missing_information=[],
        ), 100

    monkeypatch.setattr(OpenAIProvider, "structured", fake)
    for _ in range(2):
        r = client.post("/api/coach", json={"body": "O que devo revisar?"})
        assert r.status_code == 200, r.text
    assert len(calls) == 1
    assert client.get("/api/ai/status").json()["usage"]["tokens"] == 100

    def invalid(self, instruction, context, schema):
        return Advice(
            body="Inventado",
            citations=[Citation(source_id="profile", quote="Fui CEO por 20 anos")],
            missing_information=[],
        ), 20

    monkeypatch.setattr(OpenAIProvider, "structured", invalid)
    assert client.post("/api/coach", json={"body": "Conte minha história."}).status_code == 502
