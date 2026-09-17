from datetime import timedelta

from sqlalchemy import select

from app.models import Task, now
from tests.test_api import save_job


def test_restore_previous_profile_preserves_correct_current_analysis(client, user, vacancy):
    job = save_job(client, vacancy)
    original = client.get("/api/profile").json()
    changed = {**original["data"], "desired_roles": [vacancy["title"]]}
    updated = client.put(
        "/api/profile", json={"data": changed, "version": original["version"]}
    ).json()
    client.post(f"/api/jobs/{job['id']}/analyze")
    client.put("/api/profile", json={"data": original["data"], "version": updated["version"]})
    result = client.post(f"/api/jobs/{job['id']}/analyze").json()
    latest = client.get(f"/api/jobs/{job['id']}").json()
    assert latest["analysis"]["id"] == result["id"]
    assert latest["score"] == latest["analysis"]["result"]["score"]


def test_dead_worker_final_attempt_does_not_stay_running(user, database, monkeypatch):
    from app import worker

    monkeypatch.setattr(worker, "SessionLocal", database)
    with database() as db:
        db.add(
            Task(
                user_id=user["id"],
                kind="recalculate",
                status="running",
                attempts=3,
                lease_until=now() - timedelta(minutes=1),
            )
        )
        db.commit()
    assert worker.run_once()
    with database() as db:
        assert db.scalar(select(Task)).status == "failed"
