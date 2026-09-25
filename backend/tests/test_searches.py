from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app import worker
from app.integrations import search as integration
from app.models import Job, Notification, SavedJobSearch, Task, now
from app.schemas import JobData
from tests.conftest import account


def search_payload(**changes):
    return {"name": "Dados", "keywords": ["Python"], "providers": ["jooble"], **changes}


def test_saved_search_scheduler_import_restart(client, user, database, monkeypatch, vacancy):
    monkeypatch.setattr(worker, "SessionLocal", database)

    class Provider:
        def search(self, search):
            yield JobData(**vacancy, source="jooble", external_id="fixture-1")

    monkeypatch.setitem(worker.SEARCH_PROVIDERS, "jooble", Provider())
    search = client.post("/api/saved-searches", json=search_payload(cadence_hours=12)).json()
    first = client.post(f"/api/saved-searches/{search['id']}/run").json()
    assert client.post(f"/api/saved-searches/{search['id']}/run").json()["id"] == first["id"]
    assert worker.run_once()
    with database() as db:
        task = db.get(Task, first["id"])
        assert task.status == "completed"
        assert task.result["new"] == 1
        assert db.scalar(select(Job)).score is not None
        assert db.scalar(select(Notification).where(Notification.key == f"import:{task.id}"))
        saved = db.get(SavedJobSearch, search["id"])
        assert saved.next_run_at > now()
    second = client.post(f"/api/saved-searches/{search['id']}/run").json()
    with database() as db:
        task = db.get(Task, second["id"])
        task.status = "running"
        task.lease_until = now() - timedelta(minutes=1)
        task.attempts = 1
        db.commit()
    assert worker.run_once()
    with database() as db:
        result = db.get(Task, second["id"]).result
        assert result["new"] == 0 and result["deduplicated"] == 1
        assert len(db.scalars(select(Job)).all()) == 1
    account(client, "other@example.com")
    assert client.get("/api/saved-searches").json() == []
    assert client.post(f"/api/saved-searches/{search['id']}/run").status_code == 404
    assert client.delete(f"/api/saved-searches/{search['id']}").status_code == 404


def test_provider_backoff_and_disabled_search(client, user, database, monkeypatch):
    monkeypatch.setattr(worker, "SessionLocal", database)

    class Broken:
        def search(self, search):
            raise integration.ProviderError("Quota temporária", 3600)

    monkeypatch.setitem(worker.SEARCH_PROVIDERS, "jooble", Broken())
    search = client.post("/api/saved-searches", json=search_payload()).json()
    task = client.post(f"/api/saved-searches/{search['id']}/run").json()
    assert worker.run_once()
    assert not worker.run_once()
    with database() as db:
        row = db.get(Task, task["id"])
        assert row.status == "pending" and row.available_at > now() + timedelta(minutes=59)
    client.put(f"/api/saved-searches/{search['id']}", json=search_payload(enabled=False))
    assert client.post(f"/api/saved-searches/{search['id']}/run").status_code == 409


def test_jooble_normalization(monkeypatch):
    monkeypatch.setattr(
        integration,
        "request_page",
        lambda *a: {
            "jobs": [
                {
                    "id": 1,
                    "title": "Python Developer",
                    "company": "Company",
                    "location": "São Paulo",
                    "snippet": "<b>Python</b> e SQL para construir pipelines de dados.",
                    "link": "https://br.jooble.org/jdp/1",
                    "salary": "5000",
                    "type": "Full-time",
                    "updated": "2026-09-25",
                }
            ]
        },
    )
    search = SavedJobSearch(keywords=["Python"], location="SP")
    data = list(integration.Jooble().search(search))[0]
    assert data.external_id == "1" and data.source == "jooble"
    assert data.salary_min is None and data.salary_period == "unknown"
    assert data.work_model == "unknown" and data.published_at is None
    assert any(r.skill.lower() == "python" for r in data.requirements)


def test_rate_limit_sanitized(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings(), "jooble_api_key", "fixture-private-key")
    monkeypatch.setattr(integration, "reserve_request", lambda: None)
    real_client = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, headers={"Retry-After": "1200"})
    )
    monkeypatch.setattr(
        integration.httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    with pytest.raises(integration.ProviderError) as error:
        integration.request_page("Python", "SP", 1)
    assert error.value.retry_seconds == 1200
    assert "fixture-private-key" not in str(error.value)


def test_provider_budget_persists(database, monkeypatch):
    monkeypatch.setattr(integration, "SessionLocal", database)
    for _ in range(10):
        integration.reserve_request()
    with pytest.raises(integration.ProviderError):
        integration.reserve_request()


def test_cross_provider_dedupe_retains_provenance(client, user):
    text = (
        "Python SQL pipelines with documented public datasets and explicit data quality validation. "
        * 3
    )
    original = {
        "title": "Data Engineer",
        "company": "Example",
        "location": "São Paulo",
        "description": text,
        "source": "lever:example",
        "external_id": "1",
    }
    one = client.post("/api/jobs", json=original).json()
    duplicate = {**original, "description": text[:110], "source": "jooble", "external_id": "2"}
    two = client.post("/api/jobs", json=duplicate).json()
    assert two["id"] == one["id"] and not two["created"]
    assert len(two["provenance"]) == 2
    different = {**duplicate, "title": "%", "company": "%"}
    assert client.post("/api/jobs", json=different).json()["created"]


def test_dashboard_does_not_mark_later_import_as_seen(client, user, vacancy):
    snapshot = client.get("/api/dashboard/actions").json()
    client.post("/api/jobs", json=vacancy)
    assert (
        client.post("/api/dashboard/visited", json={"as_of": snapshot["as_of"]}).status_code == 200
    )
    assert client.get("/api/dashboard/actions").json()["new_since_visit"] == 1
