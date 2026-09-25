import asyncio

import httpx
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.main import app
from app.models import Job


def test_archive_committed_before_response_headers(client, user, vacancy, database):
    job_id = client.post("/api/jobs", json=vacancy).json()["id"]
    observed = []

    async def observed_app(scope, receive, send):
        async def checked_send(message):
            if message["type"] == "http.response.start":
                with database() as db:
                    observed.append(db.get(Job, job_id).archived_at is not None)
            await send(message)

        await app(scope, receive, checked_send)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=observed_app),
            base_url="http://testserver",
            cookies=client.cookies,
            headers={"X-CSRF-Token": user["csrf_token"]},
        ) as api:
            return await api.patch(f"/api/jobs/{job_id}/archive", json={"archived": True})

    assert asyncio.run(request()).status_code == 200
    assert observed == [True]


def test_commit_conflict_returns_error_and_rolls_back(client, user, vacancy, database):
    job_id = client.post("/api/jobs", json=vacancy).json()["id"]

    def conflicting_commit():
        with database() as db:
            try:
                yield db
                raise IntegrityError("commit", {}, Exception("fixture conflict"))
            finally:
                db.rollback()

    app.dependency_overrides[get_db] = conflicting_commit
    response = client.patch(f"/api/jobs/{job_id}/archive", json={"archived": True})
    assert response.status_code == 409
    with database() as db:
        assert db.get(Job, job_id).archived_at is None
