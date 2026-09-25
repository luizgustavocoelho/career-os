"""PostgreSQL portability/scheduler integration using exclusively generated fixtures."""

import os
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
target_url = os.environ.get("DATABASE_URL", "")
if not target_url.startswith("postgresql") or "careeros_test" not in target_url:
    raise SystemExit("Requires isolated PostgreSQL careeros_test database")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import worker  # noqa: E402
from app.models import Application, Document, SavedJobSearch, Task, User, now  # noqa: E402
from app.schemas import JobData  # noqa: E402
from app.services.career import analyze, save_job  # noqa: E402
from app.services.migration import MigrationConflict, migrate_sqlite  # noqa: E402

with tempfile.TemporaryDirectory(prefix="careeros-pg-fixture-") as tmp:
    source_path = Path(tmp) / "fixture.db"
    source_url = "sqlite:///" + source_path.as_posix()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env={**os.environ, "DATABASE_URL": source_url},
    )
    source = create_engine(source_url)
    target = create_engine(target_url)
    factory = sessionmaker(bind=source, expire_on_commit=False)
    with factory() as db:
        user = User(
            email=f"migration-{uuid.uuid4().hex}@example.com",
            name="Migration fixture",
            password_hash="test-fixture-not-a-real-password",
        )
        db.add(user)
        db.flush()
        user_id = user.id
        data = JobData(
            title="Python Engineer",
            company="Fixture",
            description="Python and SQL data pipelines for public data",
            source="manual",
        )
        job, _ = save_job(db, user.id, data)
        analyze(db, user, job)
        parent = Document(
            user_id=user.id,
            name="Original",
            text="Fixture original",
            content=b"%PDF-fixture-binary-preservation",
        )
        db.add(parent)
        db.flush()
        child = Document(
            user_id=user.id, name="Derived", text="Fixture derived", parent_id=parent.id
        )
        db.add(child)
        db.flush()
        app = db.scalar(select(Application).where(Application.job_id == job.id))
        app.resume_id = child.id
        db.commit()
        created_at = user.created_at
    report = migrate_sqlite(source_path, target_url, apply=False)
    with target.connect() as conn:
        assert conn.execute(select(User.id).where(User.id == user_id)).first() is None
    report = migrate_sqlite(source_path, target_url, apply=True)
    assert report["documents"]["new"] == 2
    assert report["match_analyses"]["new"] == 1 and report["application_events"]["new"] >= 1
    again = migrate_sqlite(source_path, target_url, apply=True)
    assert all(row["new"] == 0 for row in again.values())
    with target.begin() as conn:
        assert (
            conn.execute(select(User.created_at).where(User.id == user_id)).scalar_one()
            == created_at
        )
        conn.execute(
            User.__table__.update().where(User.id == user_id).values(name="Conflict fixture")
        )
    try:
        migrate_sqlite(source_path, target_url, apply=True)
        raise AssertionError("Conflict not detected")
    except MigrationConflict:
        pass
    print(
        "PostgreSQL migration: dry-run, apply, repeat, conflict, UUIDs, timestamps, PDF, lineage, timeline and analysis passed"
    )
    pg_factory = sessionmaker(bind=target, expire_on_commit=False)
    with pg_factory() as db:
        search = SavedJobSearch(
            user_id=user_id,
            name="Concurrent fixture",
            keywords=["Python"],
            providers=["jooble"],
            enabled=True,
            cadence_hours=12,
            next_run_at=now(),
        )
        db.add(search)
        db.commit()
        search_id = search.id

    class FixtureProvider:
        def search(self, search):
            yield data.model_copy(update={"source": "jooble", "external_id": "fixture-concurrent"})

    worker.SessionLocal = pg_factory
    worker.SEARCH_PROVIDERS["jooble"] = FixtureProvider()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: worker.run_once(), range(2)))
    with pg_factory() as db:
        tasks = [
            t
            for t in db.scalars(select(Task).where(Task.user_id == user_id, Task.kind == "search"))
            if t.payload.get("search_id") == search_id
        ]
        assert len(tasks) == 1 and tasks[0].status == "completed", [
            (t.status, t.error) for t in tasks
        ]
    print("PostgreSQL concurrent scheduler/worker: one task, one completion passed")
    source.dispose()
    target.dispose()
