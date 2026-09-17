from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.provider import career_coach
from app.config import settings
from app.db import get_db
from app.models import (
    AIConversation,
    AIMessage,
    Application,
    Contact,
    Job,
    Notification,
    ProfileSkill,
)
from app.schemas import CoachInput
from app.security import current_user, owned
from app.serializers import serialize
from app.services.analytics import gaps, overview, refresh_notifications, usage_summary
from app.services.career import ai_context

router = APIRouter(tags=["insights"])


@router.get("/dashboard")
@router.get("/analytics")
def dashboard(user=Depends(current_user), db: Session = Depends(get_db)):
    return overview(db, user.id)


@router.get("/gaps")
def career_gap(user=Depends(current_user), db: Session = Depends(get_db)):
    return gaps(db, user.id)


@router.get("/notifications")
def notifications(user=Depends(current_user), db: Session = Depends(get_db)):
    refresh_notifications(db, user.id)
    return [
        serialize(n)
        for n in db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
    ]


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    row = owned(db, Notification, notification_id, user.id)
    row.read = True
    return serialize(row)


@router.get("/ai/status")
def ai_status(user=Depends(current_user), db: Session = Depends(get_db)):
    return {
        "configured": bool(settings().openai_api_key),
        "model": settings().ai_model,
        "daily_limit": settings().ai_daily_limit,
        "usage": usage_summary(db, user.id),
    }


@router.get("/coach/conversations")
def conversations(user=Depends(current_user), db: Session = Depends(get_db)):
    return [
        serialize(c)
        for c in db.scalars(
            select(AIConversation)
            .where(AIConversation.user_id == user.id)
            .order_by(AIConversation.created_at.desc())
            .limit(50)
        )
    ]


@router.get("/coach/conversations/{conversation_id}")
def history(conversation_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, AIConversation, conversation_id, user.id)
    return [
        serialize(m)
        for m in db.scalars(
            select(AIMessage)
            .where(AIMessage.user_id == user.id, AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at)
            .limit(200)
        )
    ]


@router.post("/coach")
def coach(body: CoachInput, user=Depends(current_user), db: Session = Depends(get_db)):
    conversation = (
        owned(db, AIConversation, body.conversation_id, user.id) if body.conversation_id else None
    )
    if conversation and body.job_id and conversation.job_id != body.job_id:
        raise HTTPException(422, "Abra outra conversa para mudar o contexto da vaga.")
    job_id = conversation.job_id if conversation else body.job_id
    job = owned(db, Job, job_id, user.id) if job_id else None
    context = ai_context(db, user, job)
    context["question"] = body.body
    if conversation:
        messages = db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id, AIMessage.user_id == user.id)
            .order_by(AIMessage.created_at.desc())
            .limit(12)
        ).all()
        context["history"] = [{"role": m.role, "body": m.body} for m in reversed(messages)]
    reply = career_coach(db, user.id, context)
    if not conversation:
        conversation = AIConversation(user_id=user.id, job_id=job_id, title=body.body[:100])
        db.add(conversation)
        db.flush()
    db.add(AIMessage(user_id=user.id, conversation_id=conversation.id, role="user", body=body.body))
    db.add(
        AIMessage(
            user_id=user.id, conversation_id=conversation.id, role="assistant", body=reply.body
        )
    )
    return {"conversation_id": conversation.id, **reply.model_dump()}


@router.get("/search")
def search(q: str, user=Depends(current_user), db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        return {"jobs": [], "contacts": [], "skills": []}
    jobs = db.scalars(
        select(Job)
        .where(
            Job.user_id == user.id,
            or_(Job.title.icontains(q, autoescape=True), Job.company.icontains(q, autoescape=True)),
        )
        .limit(10)
    )
    contacts = db.execute(
        select(Contact, Application.job_id)
        .join(Application, Application.id == Contact.application_id)
        .where(
            Contact.user_id == user.id,
            Application.user_id == user.id,
            Contact.name.icontains(q, autoescape=True),
        )
        .limit(10)
    )
    skills = db.scalars(
        select(ProfileSkill)
        .where(ProfileSkill.user_id == user.id, ProfileSkill.name.icontains(q, autoescape=True))
        .limit(10)
    )
    return {
        "jobs": [serialize(x, exclude=("description", "data")) for x in jobs],
        "contacts": [{**serialize(contact), "job_id": job_id} for contact, job_id in contacts],
        "skills": [serialize(x) for x in skills],
    }
