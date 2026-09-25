from sqlalchemy import select

from app.models import AIConversation, AIMessage, JobSource, Task
from tests.conftest import account


def test_archive_restore_preserves_timeline(client, user, vacancy):
    job = client.post("/api/jobs", json=vacancy).json()
    path = f"/api/jobs/{job['id']}"
    assert client.delete(path, params={"confirm": job["id"]}).status_code == 409
    assert client.patch(path + "/archive", json={"archived": True}).status_code == 200
    assert client.get("/api/jobs").json()["total"] == 0
    assert client.get("/api/jobs?archived=true").json()["total"] == 1
    assert client.get("/api/analytics").json()["jobs"] == 1
    assert client.patch(path + "/archive", json={"archived": False}).status_code == 200
    events = client.get(path).json()["events"]
    assert {"discovered", "archived", "restored"} <= {e["kind"] for e in events}
    client.patch(path + "/archive", json={"archived": True})
    assert client.delete(path, params={"confirm": "wrong"}).status_code == 409
    assert client.delete(path, params={"confirm": job["id"]}).status_code == 200


def test_documents_protect_lineage(client, user):
    doc = client.post("/api/documents", json={"name": "Original", "text": "Fatos reais"}).json()
    child = client.post(
        "/api/documents", json={"name": "Versão", "text": "Fatos reais", "parent_id": doc["id"]}
    ).json()
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 409
    assert client.delete(f"/api/documents/{child['id']}").status_code == 200
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 200


def test_disabled_source_cannot_sync(client, user, database, monkeypatch):
    from app import worker

    monkeypatch.setattr(worker, "SessionLocal", database)
    source = client.post("/api/sources", json={"provider": "lever", "board": "fixture"}).json()
    client.post(f"/api/sources/{source['id']}/sync")
    client.put(
        f"/api/sources/{source['id']}",
        json={"provider": "lever", "board": "fixture", "enabled": False},
    )
    assert client.post(f"/api/sources/{source['id']}/sync").status_code == 409
    assert worker.run_once()
    with database() as db:
        assert db.scalar(select(JobSource)).last_synced_at is None
        assert db.scalar(select(Task)).status != "completed"


def test_coach_lifecycle_and_ownership(client, user, database):
    with database() as db:
        row = AIConversation(user_id=user["id"], title="Original")
        db.add(row)
        db.flush()
        db.add(AIMessage(user_id=user["id"], conversation_id=row.id, role="user", body="Olá"))
        db.commit()
        conversation_id = row.id
    path = f"/api/coach/conversations/{conversation_id}"
    assert client.patch(path, json={"title": "Renomeada"}).json()["title"] == "Renomeada"
    account(client, "another@example.com")
    assert client.delete(path).status_code == 404
    assert client.patch(path, json={"title": "Inválida"}).status_code == 404


def test_new_surfaces_require_owner_and_csrf(client, user, vacancy):
    from tests.conftest import account

    job = client.post("/api/jobs", json=vacancy).json()
    source = client.post("/api/sources", json={"provider": "lever", "board": "fixture"}).json()
    doc = client.post("/api/documents", json={"name": "private", "text": "private text"}).json()
    csrf = client.headers.pop("X-CSRF-Token")
    assert (
        client.patch(f"/api/jobs/{job['id']}/archive", json={"archived": True}).status_code == 403
    )
    client.headers["X-CSRF-Token"] = csrf
    account(client, "lifecycle-other@example.com")
    assert (
        client.patch(f"/api/jobs/{job['id']}/archive", json={"archived": True}).status_code == 404
    )
    assert client.delete(f"/api/sources/{source['id']}").status_code == 404
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/download?format=docx").status_code == 404


def test_owner_can_delete_conversation_and_messages(client, user, database):
    with database() as db:
        row = AIConversation(user_id=user["id"], title="Delete fixture")
        db.add(row)
        db.flush()
        conversation_id = row.id
        db.add(AIMessage(user_id=user["id"], conversation_id=row.id, role="user", body="Fixture"))
        db.commit()
    assert client.delete(f"/api/coach/conversations/{conversation_id}").status_code == 200
    with database() as db:
        assert (
            db.scalar(select(AIMessage).where(AIMessage.conversation_id == conversation_id)) is None
        )
