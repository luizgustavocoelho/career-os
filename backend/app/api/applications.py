from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import generate_message, prepare_interview
from app.db import get_db
from app.domain.pipeline import STATES, WAITING, change_status, event, schedule
from app.models import (
    Application,
    Contact,
    Document,
    FollowUp,
    Interview,
    Job,
    MessageDraft,
    Note,
    now,
)
from app.schemas import (
    ContactInput,
    FollowUpInput,
    InterviewInput,
    InterviewUpdate,
    MessageInput,
    StatusInput,
    TextInput,
)
from app.security import current_user, owned
from app.serializers import serialize
from app.services.career import ai_context, get_profile, latest_analysis, tailored_resume

router = APIRouter(tags=["applications"])


@router.get("/pipeline/states")
def states(user=Depends(current_user)):
    return STATES


@router.patch("/applications/{application_id}/status")
def status(
    application_id: str,
    body: StatusInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    app = owned(db, Application, application_id, user.id)
    change_status(
        db, app, body.status, body.version, get_profile(db, user).data, body.rejection_reason
    )
    db.flush()
    db.refresh(app)
    return serialize(app)


@router.post("/applications/{application_id}/notes", status_code=201)
def note(
    application_id: str, body: TextInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    app = owned(db, Application, application_id, user.id)
    row = Note(user_id=user.id, application_id=app.id, body=body.body)
    db.add(row)
    event(db, app, "note", "Nota adicionada")
    db.flush()
    return serialize(row)


@router.post("/applications/{application_id}/contacts", status_code=201)
def contact(
    application_id: str,
    body: ContactInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    app = owned(db, Application, application_id, user.id)
    row = Contact(user_id=user.id, application_id=app.id, **body.model_dump(mode="json"))
    db.add(row)
    db.flush()
    event(db, app, "contact", "Contato registrado")
    return serialize(row)


@router.post("/applications/{application_id}/messages", status_code=201)
def message(
    application_id: str,
    body: MessageInput,
    ai: bool = False,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    app = owned(db, Application, application_id, user.id)
    job = owned(db, Job, app.job_id, user.id)
    dna = get_profile(db, user).data
    if ai:
        context = ai_context(db, user, job)
        context["request"] = body.model_dump()
        text = generate_message(db, user.id, context).body
    else:
        openings = {
            "follow_up": f"Gostaria de acompanhar minha candidatura à vaga de {job.title} na {job.company}. Há alguma atualização sobre as próximas etapas?",
            "thanks": f"Agradeço pela conversa sobre a vaga de {job.title} na {job.company}. Fico à disposição para esclarecer dúvidas e seguir com as próximas etapas.",
            "reply": f"Agradeço pelo contato sobre a oportunidade de {job.title} na {job.company}. Tenho interesse em entender melhor o escopo e as próximas etapas.",
            "update": f"Gostaria de saber se há novidades no processo para {job.title} na {job.company}.",
        }
        opening = openings.get(
            body.kind, f"Tenho interesse na oportunidade de {job.title} na {job.company}."
        )
        facts = dna.get("headline", "")
        project = next((p for p in dna.get("projects", []) if p.get("description")), None)
        detail = (
            f"\n\nMeu foco profissional: {facts}."
            if facts and body.kind not in {"follow_up", "thanks", "update"}
            else ""
        )
        if project and body.kind in {"first_contact", "application", "email", "interest"}:
            detail += f"\nUm projeto que gostaria de compartilhar: {project['title']}. {project['description']}"
            if project.get("url"):
                detail += "\n" + project["url"]
        text = (
            f"Olá!\n\n{opening}{detail}\n\nObrigado pela atenção,\n{dna.get('name') or user.name}"
        )
    row = MessageDraft(user_id=user.id, application_id=app.id, kind=body.kind, body=text)
    db.add(row)
    db.flush()
    event(
        db,
        app,
        "draft",
        "Rascunho de mensagem criado",
        {"message_id": row.id, "method": "ai" if ai else "template"},
    )
    return serialize(row)


@router.put("/messages/{message_id}")
def edit_message(
    message_id: str, body: TextInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    row = owned(db, MessageDraft, message_id, user.id)
    if row.sent_at:
        raise HTTPException(
            409, "Mensagens marcadas como enviadas preservam seu conteúdo. Gere outro rascunho."
        )
    row.body = body.body
    return serialize(row)


@router.post("/messages/{message_id}/sent")
def sent(message_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    row = owned(db, MessageDraft, message_id, user.id)
    if not row.sent_at:
        row.sent_at = now()
        app = owned(db, Application, row.application_id, user.id)
        app.updated_at = now()
        event(
            db,
            app,
            "message_sent",
            "Envio de mensagem registrado pelo usuário",
            {"message_id": row.id, "kind": row.kind},
        )
        dna = get_profile(db, user).data
        if row.kind == "follow_up":
            for pending in db.scalars(
                select(FollowUp).where(
                    FollowUp.user_id == user.id,
                    FollowUp.application_id == app.id,
                    FollowUp.status == "pending",
                )
            ):
                pending.status, pending.completed_at = "sent", now()
            event(db, app, "follow_up_sent", "Follow-up enviado", {"message_id": row.id})
        if app.status in WAITING and dna.get("follow_up_enabled", True):
            schedule(db, app, now() + timedelta(days=dna.get("follow_up_days", 7)))
    return serialize(row)


@router.post("/applications/{application_id}/followups", status_code=201)
def follow(
    application_id: str,
    body: FollowUpInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    app = owned(db, Application, application_id, user.id)
    row = schedule(db, app, body.due_at)
    db.flush()
    return serialize(row)


@router.post("/followups/{followup_id}/{action}")
def follow_action(
    followup_id: str, action: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    if action not in {"sent", "cancelled", "replied"}:
        raise HTTPException(422, "Ação inválida.")
    row = owned(db, FollowUp, followup_id, user.id)
    if row.status == action:
        return serialize(row)
    if row.status not in {"pending", "sent"} or (row.status == "sent" and action != "replied"):
        raise HTTPException(409, "Este acompanhamento já foi concluído.")
    row.status, row.completed_at = action, now()
    app = owned(db, Application, row.application_id, user.id)
    app.updated_at = now()
    if action == "replied":
        for pending in db.scalars(
            select(FollowUp).where(
                FollowUp.user_id == user.id,
                FollowUp.application_id == app.id,
                FollowUp.status == "pending",
                FollowUp.id != row.id,
            )
        ):
            pending.status, pending.completed_at = "cancelled", now()
    event(
        db,
        app,
        "follow_up_" + action,
        {
            "sent": "Follow-up enviado",
            "cancelled": "Follow-up cancelado",
            "replied": "Resposta ao follow-up registrada",
        }[action],
    )
    return serialize(row)


@router.post("/applications/{application_id}/interviews", status_code=201)
def interview(
    application_id: str,
    body: InterviewInput,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    app = owned(db, Application, application_id, user.id)
    row = Interview(user_id=user.id, application_id=app.id, **body.model_dump())
    db.add(row)
    db.flush()
    event(
        db,
        app,
        "interview_scheduled",
        "Entrevista agendada: " + row.title,
        {"interview_id": row.id, "scheduled_at": row.scheduled_at.isoformat() + "Z"},
    )
    return serialize(row)


@router.put("/interviews/{interview_id}")
def edit_interview(
    interview_id: str,
    body: InterviewUpdate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    row = owned(db, Interview, interview_id, user.id)
    app = owned(db, Application, row.application_id, user.id)
    changed_feedback = row.feedback != body.feedback
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    if changed_feedback:
        event(
            db,
            app,
            "interview_feedback",
            "Feedback de entrevista registrado",
            {"interview_id": row.id, "feedback": row.feedback},
        )
    return serialize(row)


@router.post("/interviews/{interview_id}/prepare")
def prepare(
    interview_id: str, ai: bool = False, user=Depends(current_user), db: Session = Depends(get_db)
):
    row = owned(db, Interview, interview_id, user.id)
    app = owned(db, Application, row.application_id, user.id)
    job = owned(db, Job, app.job_id, user.id)
    if ai:
        context = ai_context(db, user, job)
        context["interview"] = serialize(row)
        row.preparation = prepare_interview(db, user.id, context).model_dump()
    else:
        dna = get_profile(db, user).data
        analysis = latest_analysis(db, user.id, job.id)
        gaps = analysis.result.get("blockers", []) if analysis else []
        sections = [
            f"Preparação para {job.title} · {job.company}",
            "TÓPICOS TÉCNICOS\n"
            + "\n".join(
                f"• Explique como você usaria {r['skill']} e quais limitações consideraria."
                for r in job.data.get("requirements", [])
            ),
            "PERGUNTAS COMPORTAMENTAIS\n• Conte sobre um desafio real e sua contribuição.\n• Como priorizou tarefas e comunicou dificuldades?",
            "STAR — PREENCHA COM FATOS\nSituação: qual era o contexto?\nTarefa: qual era sua responsabilidade?\nAção: o que você fez pessoalmente?\nResultado: o que mudou e como você sabe? Não invente métricas.",
            "PROJETOS DO SEU PERFIL\n"
            + "\n".join(
                f"• {p['title']}: {p.get('description', '')}" for p in dna.get("projects", [])
            ),
            "GAPS REGISTRADOS\n"
            + (", ".join(gaps) or "Nenhum gap obrigatório registrado; valide os requisitos."),
            "PERGUNTAS AO ENTREVISTADOR\n• Quais são as prioridades dos primeiros 90 dias?\n• Como o time avalia qualidade e sucesso?\n• Quais são as próximas etapas?",
            "CHECKLIST\n• Revisar a vaga\n• Selecionar exemplos reais\n• Preparar perguntas\n• Conferir horário, fuso e link",
        ]
        row.preparation = {
            "body": "\n\n".join(sections),
            "method": "rules",
            "citations": [],
            "missing_information": [],
        }
    event(
        db,
        app,
        "interview_prepared",
        "Interview Mission preparada",
        {"interview_id": row.id, "method": "ai" if ai else "rules"},
    )
    return serialize(row)


@router.post("/applications/{application_id}/resume")
def resume(application_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    app = owned(db, Application, application_id, user.id)
    job = owned(db, Job, app.job_id, user.id)
    row = Document(
        user_id=user.id,
        name=f"Currículo — {job.company}"[:240],
        kind="resume",
        text=tailored_resume(db, user, job),
        parent_id=app.resume_id,
    )
    db.add(row)
    db.flush()
    app.resume_id = row.id
    event(db, app, "resume", "Versão contextualizada do currículo criada", {"document_id": row.id})
    return serialize(row)


@router.post("/applications/{application_id}/resume/{document_id}")
def attach_resume(
    application_id: str, document_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    app = owned(db, Application, application_id, user.id)
    doc = owned(db, Document, document_id, user.id)
    app.resume_id = doc.id
    event(db, app, "resume", "Documento vinculado à candidatura", {"document_id": doc.id})
    return serialize(app)
