from datetime import timedelta

from sqlalchemy import select

from app.models import FollowUp, now
from tests.test_api import save_job


def test_high_score_with_low_coverage_is_not_dashboard_priority(client, user):
    p = client.get("/api/profile").json()
    p["data"]["work_models"] = ["remote"]
    client.put("/api/profile", json={"data": p["data"], "version": p["version"]})
    job = save_job(
        client,
        {
            "title": "Vaga sem detalhes",
            "company": "Teste",
            "description": "Descrição sem requisitos específicos ou salários.",
            "work_model": "remote",
        },
    )
    assert job["score"] == 100
    assert job["classification"] == "review"
    assert job["coverage"] == 6
    assert client.get("/api/dashboard").json()["high_matches"] == 0


def test_outgoing_message_restarts_followup_window(client, user, vacancy, database):
    job = save_job(client, vacancy)
    root = "/api/applications/" + job["application"]["id"]
    client.patch(root + "/status", json={"status": "applied", "version": 1})
    with database() as db:
        row = db.scalar(select(FollowUp))
        row.due_at = now() - timedelta(days=1)
        db.commit()
    message = client.post(root + "/messages", json={"kind": "follow_up"}).json()
    client.post(f"/api/messages/{message['id']}/sent")
    with database() as db:
        rows = db.scalars(select(FollowUp).where(FollowUp.status == "pending")).all()
        assert len(rows) == 1
        assert rows[0].due_at > now() + timedelta(days=6)
    assert client.get("/api/dashboard").json()["followups"] == []
    detail = client.get(f"/api/jobs/{job['id']}").json()
    sent = next(f for f in detail["followups"] if f["status"] == "sent")
    assert client.post(f"/api/followups/{sent['id']}/replied").status_code == 200
    assert client.get("/api/analytics").json()["replies"] == 1
    with database() as db:
        assert db.scalar(select(FollowUp).where(FollowUp.status == "pending")) is None
