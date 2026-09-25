"""Durable queue, persistent scheduler and bounded recovery. One worker for SQLite."""

import logging
import time
from datetime import timedelta

from sqlalchemy import or_, select, text

from app.db import SessionLocal
from app.domain.skills import normalize
from app.integrations.jobs import PROVIDERS
from app.integrations.search import SEARCH_PROVIDERS, ProviderError
from app.models import (
    Job,
    JobSource,
    Notification,
    SavedJobSearch,
    Task,
    User,
    WorkerHeartbeat,
    now,
)
from app.services.career import analyze, save_job
from app.services.scheduling import schedule_due

log = logging.getLogger("careeros.worker")


class Cancelled(Exception):
    pass


def search_jobs(db, search):
    for provider in search.providers:
        if provider in SEARCH_PROVIDERS:
            yield from SEARCH_PROVIDERS[provider].search(search)
        else:
            sources = db.scalars(
                select(JobSource).where(
                    JobSource.user_id == search.user_id,
                    JobSource.provider == provider,
                    JobSource.enabled.is_(True),
                )
            ).all()
            if not sources:
                raise ProviderError(
                    "Cadastre e ative uma fonte da empresa para o provider ATS selecionado."
                )
            for source in sources:
                db.refresh(source)
                if not source.enabled:
                    continue
                for data in PROVIDERS[provider].list_jobs(source.board):
                    if any(
                        normalize(term) in normalize(data.title + " " + data.description)
                        for term in search.keywords
                    ):
                        if (
                            not search.location
                            or not data.location
                            or normalize(search.location) in normalize(data.location)
                        ):
                            yield data
                source.last_synced_at = now()
                db.commit()


def matches_preferences(data, search):
    # Unknown attributes remain eligible for review, never become confirmed matches.
    if (
        search.work_models
        and data.work_model != "unknown"
        and data.work_model not in search.work_models
    ):
        return False
    if (
        search.seniority != "unknown"
        and data.seniority != "unknown"
        and data.seniority != search.seniority
    ):
        return False
    if (
        search.salary_min is not None
        and data.salary_max is not None
        and data.salary_currency == "BRL"
        and data.salary_period == "month"
        and data.salary_max < search.salary_min
    ):
        return False
    return True


def finish_search(db, task):
    if task.kind != "search":
        return
    search = db.get(SavedJobSearch, task.payload.get("search_id"))
    if search:
        search.last_run_at = now()
        search.last_status, search.last_error = task.status, task.error
        search.last_result = {k: v for k, v in (task.result or {}).items() if k != "seen"}
        search.next_run_at = (
            (
                task.available_at
                if task.status == "pending"
                else now() + timedelta(hours=search.cadence_hours)
            )
            if search.enabled and search.cadence_hours
            else None
        )


def run_once():
    with SessionLocal() as db:
        if db.bind.dialect.name != "postgresql" or db.scalar(
            text("SELECT pg_try_advisory_xact_lock(1667330659)")
        ):
            schedule_due(db)
        db.commit()
        task = db.scalar(
            select(Task)
            .where(
                or_(
                    (Task.status == "pending")
                    & or_(Task.available_at.is_(None), Task.available_at <= now()),
                    (Task.status == "running") & (Task.lease_until < now()),
                )
            )
            .order_by(Task.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not task:
            return False
        if task.attempts >= 3:
            task.status, task.active_key = "failed", None
            task.error = "A tarefa excedeu três tentativas, incluindo interrupções do worker. Execute novamente pela fonte."
            finish_search(db, task)
            db.commit()
            return True
        task.status, task.attempts, task.lease_until = (
            "running",
            task.attempts + 1,
            now() + timedelta(minutes=10),
        )
        task_id = task.id
        finish_search(db, task)
        db.commit()
        try:
            user = db.get(User, task.user_id)
            result = dict(
                task.result
                or {
                    "processed": 0,
                    "found": 0,
                    "new": 0,
                    "deduplicated": 0,
                    "high": 0,
                    "filtered": 0,
                    "seen": [],
                }
            )
            if task.kind == "recalculate":
                ids = db.scalars(select(Job.id).where(Job.user_id == user.id)).all()
                for job_id in ids:
                    analyze(db, user, db.get(Job, job_id))
                    result["processed"] += 1
                    task.lease_until = now() + timedelta(minutes=10)
                    db.commit()
            elif task.kind in {"sync", "search"}:
                search = None
                source = None
                if task.kind == "sync":
                    source = db.get(JobSource, task.payload["source_id"])
                    if not source or source.user_id != user.id or not source.enabled:
                        raise Cancelled()
                    items = PROVIDERS[source.provider].list_jobs(source.board)
                else:
                    search = db.get(SavedJobSearch, task.payload["search_id"])
                    if not search or search.user_id != user.id or not search.enabled:
                        raise Cancelled()
                    items = search_jobs(db, search)
                db.commit()
                for data in items:
                    control = (
                        db.get(SavedJobSearch, search.id, populate_existing=True)
                        if search
                        else db.get(JobSource, source.id, populate_existing=True)
                    )
                    if not control or not control.enabled:
                        raise Cancelled()
                    identity = (
                        data.source
                        + ":"
                        + (data.external_id or data.url or data.title + data.company)
                    )
                    if identity in result["seen"]:
                        db.commit()
                        continue
                    result["found"] += 1
                    if search and not matches_preferences(data, search):
                        result["filtered"] += 1
                    else:
                        job, created = save_job(db, user.id, data)
                        if created:
                            analyze(db, user, job)
                            result["new"] += 1
                            result["high"] += int(job.classification == "high")
                        else:
                            result["deduplicated"] += 1
                        result["processed"] += 1
                    result["seen"] = [*result["seen"], identity]
                    task.result = dict(result)
                    task.lease_until = now() + timedelta(minutes=10)
                    db.get(WorkerHeartbeat, "scheduler").updated_at = now()
                    db.commit()
                if source:
                    source.last_synced_at = now()
                if result["new"]:
                    key = f"import:{task.id}"
                    if not db.scalar(
                        select(Notification.id).where(
                            Notification.user_id == user.id, Notification.key == key
                        )
                    ):
                        db.add(
                            Notification(
                                user_id=user.id,
                                key=key,
                                title=f"{result['new']} novas vagas encontradas; {result['high']} com prioridade alta.",
                            )
                        )
            else:
                raise ValueError("Tipo de tarefa inválido")
            task.status, task.result, task.error, task.active_key = "completed", result, None, None
            finish_search(db, task)
            db.commit()
        except Cancelled:
            db.rollback()
            task = db.get(Task, task_id)
            task.status, task.active_key, task.error = (
                "cancelled",
                None,
                "Fonte ou busca desativada/removida.",
            )
            finish_search(db, task)
            db.commit()
        except Exception as exc:
            db.rollback()
            task = db.get(Task, task_id)
            task.status = "failed" if task.attempts >= 3 else "pending"
            task.active_key = None if task.status == "failed" else task.active_key
            task.error = (
                str(exc)
                if isinstance(exc, ProviderError)
                else "Falha ao processar. Verifique fonte e conexão."
            )
            task.available_at = now() + timedelta(
                seconds=max(60 * 2**task.attempts, getattr(exc, "retry_seconds", 0))
            )
            finish_search(db, task)
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
