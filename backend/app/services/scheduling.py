"""Persistent scheduling using the existing queue. SQLite requires one worker."""

from datetime import timedelta

from sqlalchemy import select

from app.models import SavedJobSearch, Task, WorkerHeartbeat, now


def enqueue(db, search):
    existing = db.scalar(select(Task).where(Task.active_key == f"search:{search.id}"))
    if existing:
        return existing
    task = Task(
        user_id=search.user_id,
        kind="search",
        payload={"search_id": search.id},
        active_key=f"search:{search.id}",
    )
    db.add(task)
    search.last_status = "pending"
    db.flush()
    return task


def schedule_due(db):
    heartbeat = db.get(WorkerHeartbeat, "scheduler")
    if heartbeat is None:
        # PostgreSQL scheduler lock (taken by caller) also serializes first insertion.
        heartbeat = WorkerHeartbeat(id="scheduler")
        db.add(heartbeat)
    heartbeat.updated_at = now()
    searches = db.scalars(
        select(SavedJobSearch)
        .where(
            SavedJobSearch.enabled.is_(True),
            SavedJobSearch.cadence_hours.is_not(None),
            SavedJobSearch.next_run_at <= now(),
        )
        .with_for_update(skip_locked=True)
    )
    for search in searches:
        enqueue(db, search)
        search.next_run_at = now() + timedelta(hours=search.cadence_hours)
