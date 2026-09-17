from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from app.ai.provider import analyze_match, parse_job
from app.db import get_db
from app.domain.parsers import local_job
from app.domain.skills import canonical_url, fingerprint, normalize
from app.integrations.jobs import from_url
from app.models import (
    Application,
    ApplicationEvent,
    Contact,
    FollowUp,
    Interview,
    Job,
    JobRequirement,
    JobSource,
    MatchAnalysis,
    MessageDraft,
    Note,
    Task,
)
from app.schemas import JobData, ParseInput, SourceInput, UrlInput
from app.security import current_user, owned
from app.serializers import serialize
from app.services.career import ai_context, analyze, latest_analysis, save_job

router = APIRouter(tags=["jobs"])


@router.post("/jobs/parse")
def parse(
    body: ParseInput, ai: bool = False, user=Depends(current_user), db: Session = Depends(get_db)
):
    result = parse_job(db, user.id, body.text) if ai else local_job(body.text)
    return {"data": result.model_dump(), "method": "ai" if ai else "local", "review_required": True}


@router.post("/jobs/from-url")
def url(body: UrlInput, user=Depends(current_user)):
    return {
        "data": from_url(body.url).model_dump(),
        "method": "public_api",
        "review_required": True,
    }


@router.post("/jobs", status_code=201)
def create(body: JobData, user=Depends(current_user), db: Session = Depends(get_db)):
    job, created = save_job(db, user.id, body)
    analysis = analyze(db, user, job)
    return {**serialize(job), "created": created, "analysis": analysis.result}


@router.get("/jobs")
def listing(
    q: str = "",
    company: str = "",
    location: str = "",
    work_model: str = "",
    seniority: str = "",
    source: str = "",
    skill: str = "",
    status: str = "",
    favorite: bool = False,
    min_score: float | None = None,
    min_salary: float | None = None,
    since: datetime | None = None,
    sort: str = "recent",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Job, Application)
        .join(Application, Application.job_id == Job.id)
        .where(Job.user_id == user.id, Application.user_id == user.id)
    )
    for column, value in ((Job.company, company), (Job.location, location)):
        if value:
            query = query.where(column.icontains(value, autoescape=True))
    if q:
        query = query.where(
            or_(
                Job.title.icontains(q, autoescape=True),
                Job.company.icontains(q, autoescape=True),
                Job.description.icontains(q, autoescape=True),
            )
        )
    for column, value in (
        (Job.work_model, work_model),
        (Job.seniority, seniority),
        (Job.source, source),
        (Application.status, status),
    ):
        if value:
            query = query.where(column == value)
    if skill:
        query = query.where(
            Job.id.in_(
                select(JobRequirement.job_id).where(
                    JobRequirement.user_id == user.id, JobRequirement.skill == normalize(skill)
                )
            )
        )
    if favorite:
        query = query.where(Job.favorite.is_(True))
    if min_score is not None:
        query = query.where(Job.score >= min_score)
    if min_salary is not None:
        query = query.where(Job.salary_max >= min_salary)
    if since:
        query = query.where(Job.created_at >= since.replace(tzinfo=None))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    order = {
        "score": Job.score.desc().nullslast(),
        "priority": case(
            (Job.classification == "high", 4),
            (Job.classification == "worth", 3),
            (Job.classification == "review", 2),
            (Job.classification == "low", 1),
            else_=0,
        ).desc(),
        "salary": Job.salary_max.desc().nullslast(),
    }.get(sort, Job.created_at.desc())
    rows = db.execute(
        query.order_by(order, Job.score.desc().nullslast(), Job.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "items": [
            {**serialize(j, exclude=("description", "data")), "application": serialize(a)}
            for j, a in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/jobs/{job_id}")
def detail(job_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    job = owned(db, Job, job_id, user.id)
    app = db.scalar(
        select(Application).where(Application.job_id == job.id, Application.user_id == user.id)
    )
    analysis = latest_analysis(db, user.id, job.id)
    result = {
        **serialize(job),
        "application": serialize(app),
        "analysis": serialize(analysis, exclude=("snapshot",)) if analysis else None,
        "analysis_stale": job.score is None,
    }
    for model, key in (
        (ApplicationEvent, "events"),
        (Note, "notes"),
        (Contact, "contacts"),
        (MessageDraft, "messages"),
        (FollowUp, "followups"),
        (Interview, "interviews"),
    ):
        result[key] = [
            serialize(r)
            for r in db.scalars(
                select(model)
                .where(model.user_id == user.id, model.application_id == app.id)
                .order_by(model.created_at.desc())
                .limit(300)
            )
        ]
    return result


@router.post("/jobs/{job_id}/analyze")
def score(job_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return serialize(analyze(db, user, owned(db, Job, job_id, user.id)), exclude=("snapshot",))


@router.put("/jobs/{job_id}")
def edit_job(job_id: str, body: JobData, user=Depends(current_user), db: Session = Depends(get_db)):
    from app.domain.pipeline import event

    job = owned(db, Job, job_id, user.id)
    raw = body.model_dump(mode="json")
    raw["url"] = canonical_url(raw.get("url")) or None
    job.data, job.fingerprint = raw, fingerprint(raw)
    for key in (
        "title",
        "company",
        "location",
        "description",
        "url",
        "source",
        "external_id",
        "work_model",
        "seniority",
        "salary_min",
        "salary_max",
    ):
        setattr(job, key, raw[key])
    db.execute(
        delete(JobRequirement).where(
            JobRequirement.job_id == job.id, JobRequirement.user_id == user.id
        )
    )
    seen = set()
    for req in body.requirements:
        key = normalize(req.skill)
        if key not in seen:
            db.add(
                JobRequirement(
                    user_id=user.id,
                    job_id=job.id,
                    skill=key,
                    mandatory=req.mandatory,
                    description=req.description,
                )
            )
            seen.add(key)
    app = db.scalar(
        select(Application).where(Application.job_id == job.id, Application.user_id == user.id)
    )
    event(db, app, "job_edited", "Dados da vaga revisados pelo usuário")
    analyze(db, user, job)
    return serialize(job)


@router.post("/jobs/{job_id}/semantic")
def semantic(job_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return analyze_match(
        db, user.id, ai_context(db, user, owned(db, Job, job_id, user.id))
    ).model_dump()


@router.post("/jobs/{job_id}/favorite")
def favorite_job(job_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    job = owned(db, Job, job_id, user.id)
    job.favorite = not job.favorite
    return {"favorite": job.favorite}


@router.get("/sources")
def sources(user=Depends(current_user), db: Session = Depends(get_db)):
    return [serialize(r) for r in db.scalars(select(JobSource).where(JobSource.user_id == user.id))]


@router.post("/sources", status_code=201)
def add_source(body: SourceInput, user=Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(
        select(JobSource).where(
            JobSource.user_id == user.id,
            JobSource.provider == body.provider,
            JobSource.board == body.board,
        )
    )
    if not row:
        row = JobSource(user_id=user.id, **body.model_dump())
        db.add(row)
        db.flush()
    return serialize(row)


@router.post("/sources/{source_id}/sync", status_code=202)
def sync(source_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    owned(db, JobSource, source_id, user.id)
    tasks = db.scalars(
        select(Task).where(
            Task.user_id == user.id, Task.kind == "sync", Task.status.in_(["pending", "running"])
        )
    )
    for t in tasks:
        if t.payload.get("source_id") == source_id:
            return serialize(t)
    task = Task(user_id=user.id, kind="sync", payload={"source_id": source_id})
    db.add(task)
    db.flush()
    return serialize(task)


@router.get("/tasks")
def tasks(user=Depends(current_user), db: Session = Depends(get_db)):
    return [
        serialize(t)
        for t in db.scalars(
            select(Task).where(Task.user_id == user.id).order_by(Task.created_at.desc()).limit(30)
        )
    ]


@router.get("/analyses/{analysis_id}")
def audit(analysis_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return serialize(owned(db, MatchAnalysis, analysis_id, user.id))
