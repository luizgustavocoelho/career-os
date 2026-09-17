"""CI-only smoke against the migrated disposable PostgreSQL service."""

import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.security import user_count  # noqa: E402
from app.worker import run_once  # noqa: E402

if (
    not settings().database_url.startswith("postgresql")
    or "careeros_test" not in settings().database_url
):
    raise SystemExit("Use apenas o banco PostgreSQL careeros_test descartável.")

with TestClient(app) as client:
    register = client.post(
        "/api/auth/register",
        json={
            "name": "CI",
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "isolated-ci-password-123",
        },
    )
    assert register.status_code == 201, register.text
    client.headers["X-CSRF-Token"] = register.json()["csrf_token"]
    job = client.post(
        "/api/jobs",
        json={
            "title": "Data Engineer",
            "company": "CI fixture",
            "description": "Build Python and SQL pipelines for public data.",
            "requirements": [{"skill": "Python", "mandatory": True}],
        },
    )
    assert job.status_code == 201, job.text
    detail = client.get("/api/jobs/" + job.json()["id"]).json()
    moved = client.patch(
        "/api/applications/" + detail["application"]["id"] + "/status",
        json={"status": "applied", "version": 1},
    )
    assert moved.status_code == 200, moved.text
    assert client.get("/api/analytics").json()["applications"] == 1
    assert client.post("/api/profile/skills", json={"name": "Python"}).status_code == 201
    assert run_once()
    assert client.get("/api/jobs/" + job.json()["id"]).json()["score"] is not None

with SessionLocal() as db:
    settings().registration_limit = user_count(db) + 1


def register_concurrently(_):
    with TestClient(app) as concurrent:
        return concurrent.post(
            "/api/auth/register",
            json={
                "name": "Concurrent CI",
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": "isolated-ci-password-123",
            },
        ).status_code


with ThreadPoolExecutor(max_workers=2) as pool:
    assert sorted(pool.map(register_concurrently, range(2))) == [201, 403]
print("PostgreSQL smoke passed")
