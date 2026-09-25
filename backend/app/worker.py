"""Durable task worker: PostgreSQL SKIP LOCKED; one worker recommended for SQLite."""

import logging
import time
from datetime import timedelta

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.integrations.jobs import PROVIDERS
from app.models import Job, JobSource, Task, User, now
from app.services.career import analyze, save_job

log = logging.getLogger("careeros.worker")


def run_once():
    with SessionLocal() as db:
        task = db.scalar(
            select(Task)
            .where(
                or_(
                    Task.status == "pending",
                    (Task.status == "running") & (Task.lease_until < now()),
                ),
            )
            .order_by(Task.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not task:
            return False
        if task.attempts >= 3:
            task.status = "failed"
            task.error = "A tarefa excedeu três tentativas, incluindo interrupções do worker. Execute novamente pela fonte."
            db.commit()
            return True
        task.status, task.attempts, task.lease_until = (
            "running",
            task.attempts + 1,
            now() + timedelta(minutes=10),
        )
        task_id = task.id
        db.commit()
        try:
            user = db.get(User, task.user_id)
            count = 0
            if task.kind == "recalculate":
                # Process in pages; commit checkpoints, so restart never discards completed analyses.
                ids = db.scalars(select(Job.id).where(Job.user_id == user.id)).all()
                for job_id in ids:
                    analyze(db, user, db.get(Job, job_id))
                    count += 1
                    task.lease_until = now() + timedelta(minutes=10)
                    db.commit()
            elif task.kind == "sync":
                source = db.scalar(
                    select(JobSource).where(
                        JobSource.id == task.payload["source_id"], JobSource.user_id == user.id
                    )
                )
                if not source or not source.enabled:
                    raise ValueError("Fonte removida")
                for data in PROVIDERS[source.provider].list_jobs(source.board):
                    job, created = save_job(db, user.id, data)
                    if created:
                        analyze(db, user, job)
                        count += 1
                    task.lease_until = now() + timedelta(minutes=10)
                    db.commit()
                source.last_synced_at = now()
            else:
                raise ValueError("Tipo de tarefa inválido")
            task.status, task.result, task.error = "completed", {"processed": count}, None
            db.commit()
        except Exception as exc:
            db.rollback()
            task = db.get(Task, task_id)
            task.status = "failed" if task.attempts >= 3 else "pending"
            task.error = "Falha ao processar. Verifique a fonte e a conexão; tentativas: " + str(
                task.attempts
            )
            db.commit()
            log.error("task_failed id=%s type=%s", task_id, type(exc).__name__)
        return True


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            worked = run_once()
        except Exception as exc:
            log.error("worker_error type=%s", type(exc).__name__)
            worked = False
        time.sleep(1 if worked else 5)


if __name__ == "__main__":
    main()
