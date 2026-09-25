import json

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text

from app.domain.pipeline import event
from app.domain.scoring import calculate
from app.domain.skills import canonical_url, fingerprint, normalize
from app.models import (
    Application,
    Contact,
    Document,
    Evidence,
    Job,
    JobRequirement,
    MatchAnalysis,
    MatchComponent,
    Notification,
    Profile,
    ProfileSkill,
)
from app.schemas import DNA, JobData
from app.serializers import serialize


def get_profile(db, user):
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id, data=DNA(name=user.name, email=user.email).model_dump())
        db.add(profile)
        db.flush()
    return profile


def skill_list(db, user_id):
    skills = db.scalars(
        select(ProfileSkill).where(ProfileSkill.user_id == user_id).order_by(ProfileSkill.name)
    ).all()
    evidence = db.scalars(select(Evidence).where(Evidence.user_id == user_id)).all()
    by_skill = {}
    for item in evidence:
        by_skill.setdefault(item.skill_id, []).append(serialize(item))
    return [{**serialize(s), "evidence": by_skill.get(s.id, [])} for s in skills]


def save_job(db, user_id, data: JobData):
    if db.bind.dialect.name == "postgresql":
        # Serialize ingestion per owner through commit, including manual imports.
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:owner, 0))"), {"owner": user_id}
        )
    raw = data.model_dump(mode="json")
    raw["url"] = canonical_url(raw.get("url")) or None
    fp = fingerprint(raw)
    conditions = [Job.fingerprint == fp]
    if raw["url"]:
        conditions.append(Job.url == raw["url"])
    if data.external_id:
        conditions.append((Job.source == data.source) & (Job.external_id == data.external_id))
    existing = db.scalar(select(Job).where(Job.user_id == user_id, or_(*conditions)))
    origin = {"source": data.source, "external_id": data.external_id, "url": raw["url"]}
    if not existing and data.company and data.location:
        # Conservative cross-provider match: same identity and a substantial shared description.
        from difflib import SequenceMatcher

        candidates = db.scalars(
            select(Job).where(
                Job.user_id == user_id,
                func.lower(Job.company) == data.company.lower(),
                func.lower(Job.title) == data.title.lower(),
            )
        )
        for candidate in candidates:
            if normalize(candidate.location) != normalize(data.location):
                continue
            a, b = normalize(candidate.description), normalize(data.description)
            if min(len(a), len(b)) >= 80 and (
                a.startswith(b)
                or b.startswith(a)
                or SequenceMatcher(None, a[:6000], b[:6000]).ratio() >= 0.94
            ):
                existing = candidate
                break
    if existing:
        origins = existing.provenance or [
            {"source": existing.source, "external_id": existing.external_id, "url": existing.url}
        ]
        if origin not in origins:
            existing.provenance = [*origins, origin]
        return existing, False
    job = Job(
        user_id=user_id,
        fingerprint=fp,
        data=raw,
        provenance=[origin],
        **{
            k: raw[k]
            for k in (
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
            )
        },
    )
    db.add(job)
    db.flush()
    seen = set()
    for req in data.requirements:
        normalized = normalize(req.skill)
        if normalized not in seen:
            db.add(
                JobRequirement(
                    user_id=user_id,
                    job_id=job.id,
                    skill=normalized,
                    mandatory=req.mandatory,
                    description=req.description,
                )
            )
            seen.add(normalized)
    app = Application(user_id=user_id, job_id=job.id)
    db.add(app)
    db.flush()
    event(db, app, "discovered", "Vaga adicionada ao radar", {"source": data.source})
    return job, True


def analyze(db, user, job):
    profile = get_profile(db, user)
    skills = skill_list(db, user.id)
    result = calculate(profile.data, skills, job.data)
    prior = db.scalar(
        select(MatchAnalysis)
        .where(
            MatchAnalysis.user_id == user.id,
            MatchAnalysis.job_id == job.id,
        )
        .order_by(MatchAnalysis.created_at.desc())
    )
    if prior and prior.input_hash == result["input_hash"]:
        job.score = prior.score
        job.classification = prior.classification
        job.coverage = prior.result["coverage"]
        return prior
    analysis = MatchAnalysis(
        user_id=user.id,
        job_id=job.id,
        score=result["score"],
        classification=result["classification"],
        algorithm=result["algorithm"],
        input_hash=result["input_hash"],
        result=result,
        snapshot={
            "profile": profile.data,
            "profile_version": profile.version,
            "skills": skills,
            "job": job.data,
        },
    )
    db.add(analysis)
    db.flush()
    for component in result["components"]:
        db.add(MatchComponent(user_id=user.id, analysis_id=analysis.id, **component))
    job.score = result["score"]
    job.classification = result["classification"]
    job.coverage = result["coverage"]
    app = db.scalar(
        select(Application).where(Application.job_id == job.id, Application.user_id == user.id)
    )
    event(
        db,
        app,
        "analyzed",
        f"Opportunity Score calculado: {job.score}%",
        {"analysis_id": analysis.id, "score": job.score},
    )
    if result["classification"] == "high":
        key = "match:" + analysis.id
        db.add(
            Notification(
                user_id=user.id,
                key=key,
                title=f"{job.title}: {job.score}% de compatibilidade",
                job_id=job.id,
            )
        )
    return analysis


def latest_analysis(db, user_id, job_id):
    return db.scalar(
        select(MatchAnalysis)
        .where(MatchAnalysis.user_id == user_id, MatchAnalysis.job_id == job_id)
        .order_by(MatchAnalysis.created_at.desc())
    )


def ai_context(db, user, job=None):
    profile = get_profile(db, user).data.copy()
    # Contact details, salary preferences and original PDF are unnecessary for coaching.
    for key in (
        "email",
        "phone",
        "salary_min",
        "salary_currency",
        "salary_period",
        "ai_consent",
        "follow_up_days",
        "follow_up_enabled",
    ):
        profile.pop(key, None)
    sources = {"profile": json.dumps(profile, ensure_ascii=False)}
    for skill in skill_list(db, user.id):
        sources["skill:" + skill["id"]] = json.dumps(skill, ensure_ascii=False)
    if job:
        sources["job:" + job.id] = json.dumps(job.data, ensure_ascii=False)
        analysis = latest_analysis(db, user.id, job.id)
        if analysis:
            sources["analysis:" + analysis.id] = json.dumps(analysis.result, ensure_ascii=False)
        app = db.scalar(
            select(Application).where(Application.job_id == job.id, Application.user_id == user.id)
        )
        sources["application:" + app.id] = json.dumps(
            {"status": app.status, "rejection_reason": app.rejection_reason}, ensure_ascii=False
        )
        from app.models import ApplicationEvent, Interview, MessageDraft, Note

        for model, prefix in (
            (ApplicationEvent, "event"),
            (Interview, "interview"),
            (MessageDraft, "draft"),
            (Note, "note"),
        ):
            for row in db.scalars(
                select(model)
                .where(model.user_id == user.id, model.application_id == app.id)
                .order_by(model.created_at.desc())
                .limit(8)
            ):
                sources[prefix + ":" + row.id] = json.dumps(serialize(row), ensure_ascii=False)[
                    :5000
                ]
        for row in db.scalars(
            select(Contact)
            .where(Contact.user_id == user.id, Contact.application_id == app.id)
            .limit(5)
        ):
            sources["contact:" + row.id] = json.dumps(
                {"name": row.name, "role": row.role}, ensure_ascii=False
            )
        if app.resume_id:
            doc = db.scalar(
                select(Document).where(Document.id == app.resume_id, Document.user_id == user.id)
            )
            if doc:
                sources["resume:" + doc.id] = doc.text[:18000]
    # Bound serialized context to prevent accidental unbounded API spending.
    if len(json.dumps(sources)) > 100000:
        raise HTTPException(
            422,
            "Contexto muito extenso. Reduza notas ou descrições do perfil antes de consultar a IA.",
        )
    return {"sources": sources}


def tailored_resume(db, user, job, selection=None):
    profile = get_profile(db, user)
    dna = profile.data
    if selection and selection.profile_version != profile.version:
        raise HTTPException(409, "O perfil mudou. Recarregue e revise a seleção.")
    required = {normalize(r["skill"]) for r in job.data.get("requirements", [])}
    skills = skill_list(db, user.id)
    ordered = sorted(skills, key=lambda s: normalize(s["name"]) not in required)
    lines = [
        dna.get("name", user.name),
        dna.get("headline", ""),
        dna.get("location", ""),
        " · ".join(
            x
            for x in (dna.get("email"), dna.get("phone"), dna.get("linkedin"), dna.get("portfolio"))
            if x
        ),
        "",
        dna.get("summary", ""),
    ]
    if ordered:
        lines += ["", "COMPETÊNCIAS", ", ".join(s["name"] for s in ordered)]
    for field, label in (
        ("experiences", "EXPERIÊNCIA"),
        ("projects", "PROJETOS"),
        ("education", "FORMAÇÃO"),
        ("certifications", "CERTIFICAÇÕES"),
    ):
        entries = dna.get(field, [])
        if selection and field in {"experiences", "projects"}:
            indexes = getattr(selection, field)
            if indexes is not None:
                if any(i < 0 or i >= len(entries) for i in indexes):
                    raise HTTPException(422, "Seleção de experiência/projeto inválida.")
                entries = [entries[i] for i in dict.fromkeys(indexes)]
        if field in {"experiences", "projects"}:
            entries = sorted(
                entries,
                key=lambda item: (
                    -sum(
                        skill
                        in normalize(item.get("title", "") + " " + item.get("description", ""))
                        for skill in required
                    )
                ),
            )
        if entries:
            lines += ["", label]
            for item in entries:
                lines += [
                    item["title"]
                    + (" — " + item["organization"] if item.get("organization") else ""),
                    " – ".join(filter(None, (item.get("start"), item.get("end")))),
                    item.get("description", ""),
                    item.get("url", ""),
                ]
    return "\n".join(lines).strip()
