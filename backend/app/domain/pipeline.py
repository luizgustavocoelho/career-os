from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update

from app.models import Application, ApplicationEvent, FollowUp, now

STATES = {
    "discovered": "Descoberta",
    "saved": "Salva",
    "analyzing": "Analisando",
    "preparing": "Preparando candidatura",
    "applied": "Candidatura enviada",
    "recruiter": "Contato com recrutador",
    "screening": "Triagem RH",
    "hr_interview": "Entrevista RH",
    "technical": "Entrevista técnica",
    "case": "Case / Teste",
    "final": "Entrevista final",
    "offer": "Oferta",
    "hired": "Contratado",
    "rejected": "Rejeitado",
    "withdrawn": "Desistência",
    "no_response": "Sem resposta",
}
TERMINAL = {"hired", "rejected", "withdrawn"}
WAITING = {
    "applied",
    "recruiter",
    "screening",
    "hr_interview",
    "technical",
    "case",
    "final",
    "no_response",
}


def event(db, app, kind, title, data=None):
    db.add(
        ApplicationEvent(
            user_id=app.user_id, application_id=app.id, kind=kind, title=title, data=data or {}
        )
    )


def schedule(db, app, due_at):
    existing = db.scalar(
        select(FollowUp).where(FollowUp.application_id == app.id, FollowUp.status == "pending")
    )
    if existing:
        existing.status = "cancelled"
        existing.completed_at = now()
    follow = FollowUp(user_id=app.user_id, application_id=app.id, due_at=due_at)
    db.add(follow)
    event(
        db,
        app,
        "follow_up_scheduled",
        "Acompanhamento agendado",
        {"due_at": due_at.isoformat() + "Z"},
    )
    return follow


def change_status(db, app, status, version, dna, rejection_reason=None):
    if status not in STATES:
        raise HTTPException(422, "Etapa inválida.")
    previous = app.status
    result = db.execute(
        update(Application)
        .where(Application.id == app.id, Application.version == version)
        .values(
            status=status, version=version + 1, updated_at=now(), rejection_reason=rejection_reason
        )
    )
    if not result.rowcount:
        raise HTTPException(409, "A candidatura foi alterada em outra janela. Atualize a página.")
    if previous == status:
        return
    event(
        db,
        app,
        "status_changed",
        f"{STATES[previous]} → {STATES[status]}",
        {"from": previous, "to": status, "rejection_reason": rejection_reason},
    )
    for follow in db.scalars(
        select(FollowUp).where(FollowUp.application_id == app.id, FollowUp.status == "pending")
    ):
        follow.status = "cancelled"
        follow.completed_at = now()
    if status in WAITING and dna.get("follow_up_enabled", True):
        schedule(db, app, now() + timedelta(days=dna.get("follow_up_days", 7)))
