from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select

from app.domain.pipeline import STATES, TERMINAL
from app.domain.skills import normalize
from app.models import (
    AIUsage,
    Application,
    ApplicationEvent,
    FollowUp,
    Interview,
    Job,
    JobRequirement,
    Notification,
    ProfileSkill,
    now,
)


def gaps(db, user_id):
    jobs = db.scalars(select(Job).where(Job.user_id == user_id, Job.score >= 40)).all()
    ids = [j.id for j in jobs]
    skills = {
        s.normalized: s
        for s in db.scalars(select(ProfileSkill).where(ProfileSkill.user_id == user_id))
    }
    counts = Counter()
    mandatory = Counter()
    by_skill = defaultdict(set)
    if ids:
        for req in db.scalars(
            select(JobRequirement).where(
                JobRequirement.user_id == user_id, JobRequirement.job_id.in_(ids)
            )
        ):
            by_skill[normalize(req.skill)].add(req.job_id)
            if req.mandatory:
                mandatory[normalize(req.skill)] += 1
        counts.update({k: len(v) for k, v in by_skill.items()})
    rows = []
    for name, count in counts.most_common():
        skill = skills.get(name)
        category = (
            "missing" if not skill else "weak" if skill.developing or skill.level <= 2 else "strong"
        )
        rows.append(
            {
                "skill": name,
                "count": count,
                "percentage": round(100 * count / len(ids), 1),
                "category": category,
                "mandatory_count": mandatory[name],
                "high_impact": category != "strong" and count / len(ids) >= 0.3,
            }
        )
    return {
        "sample_size": len(ids),
        "scope": "Vagas com score atual ≥ 40. Frequência indica demanda na sua amostra, não causalidade.",
        "skills": rows,
    }


def overview(db, user_id):
    apps = db.scalars(select(Application).where(Application.user_id == user_id)).all()
    jobs = db.scalars(select(Job).where(Job.user_id == user_id)).all()
    events = db.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.user_id == user_id)
        .order_by(ApplicationEvent.created_at)
    ).all()
    interviews = db.scalars(select(Interview).where(Interview.user_id == user_id)).all()
    followups = db.scalars(
        select(FollowUp).where(
            FollowUp.user_id == user_id, FollowUp.status == "pending", FollowUp.due_at <= now()
        )
    ).all()
    reached = defaultdict(set)
    durations = defaultdict(list)
    previous = {}
    weekly = Counter()
    for e in events:
        if e.kind == "status_changed":
            target = e.data.get("to")
            reached[target].add(e.application_id)
            if e.application_id in previous:
                prev = previous[e.application_id]
                durations[prev.data.get("to") + " → " + target].append(
                    (e.created_at - prev.created_at).total_seconds() / 86400
                )
            previous[e.application_id] = e
            if target == "applied":
                week = (e.created_at - timedelta(days=e.created_at.weekday())).date().isoformat()
                weekly[week] += 1
    applied_ids = reached["applied"]
    replied_ids = set().union(
        *(
            reached[s]
            for s in (
                "screening",
                "hr_interview",
                "technical",
                "case",
                "final",
                "offer",
                "hired",
                "rejected",
            )
        )
    )
    replied_ids.update(e.application_id for e in events if e.kind == "follow_up_replied")
    jobs_by_id = {j.id: j for j in jobs}
    app_by_id = {a.id: a for a in apps}
    interview_apps = {i.application_id for i in interviews}
    sources, roles = (
        defaultdict(lambda: {"applications": 0, "interviews": 0}),
        defaultdict(lambda: {"applications": 0, "interviews": 0}),
    )
    for a in apps:
        j = jobs_by_id[a.job_id]
        for group, key in ((sources, j.source), (roles, j.title)):
            group[key]["applications"] += int(a.id in applied_ids)
            group[key]["interviews"] += int(a.id in interview_apps)
    pipeline = [
        {
            "status": s,
            "label": label,
            "count": sum(a.status == s for a in apps),
            "ever_reached": len(reached[s]),
        }
        for s, label in STATES.items()
    ]
    upcoming = sorted(
        [i for i in interviews if i.scheduled_at >= now()], key=lambda i: i.scheduled_at
    )

    def opportunity(a_id):
        a = app_by_id[a_id]
        j = jobs_by_id[a.job_id]
        return {"job_id": j.id, "title": j.title, "company": j.company}

    return {
        "jobs": len(jobs),
        "analyzed": sum(j.score is not None for j in jobs),
        "high_matches": sum(j.classification == "high" for j in jobs),
        "new_jobs": sum(j.created_at >= now() - timedelta(days=7) for j in jobs),
        "applications": len(applied_ids),
        "replies": len(replied_ids & applied_ids),
        "response_rate": round(100 * len(replied_ids & applied_ids) / len(applied_ids), 1)
        if applied_ids
        else None,
        "application_rate": round(100 * len(applied_ids) / len(jobs), 1) if jobs else None,
        "interview_count": len(interviews),
        "technical_interviews": sum(i.kind == "technical" for i in interviews),
        "offers": len(reached["offer"]),
        "rejections": len(reached["rejected"]),
        "waiting": sum(
            a.id in applied_ids and a.status not in TERMINAL and a.status != "offer" for a in apps
        ),
        "no_response": len(reached["no_response"]),
        "pipeline": pipeline,
        "followups": [
            {**opportunity(f.application_id), "id": f.id, "due_at": f.due_at.isoformat() + "Z"}
            for f in followups
            if app_by_id[f.application_id].status not in TERMINAL
        ],
        "upcoming": [
            {
                **opportunity(i.application_id),
                "id": i.id,
                "title": i.title,
                "scheduled_at": i.scheduled_at.isoformat() + "Z",
            }
            for i in upcoming[:10]
        ],
        "weekly": [{"week": k, "applications": v} for k, v in sorted(weekly.items())[-12:]],
        "sources": dict(sources),
        "roles": dict(roles),
        "transition_days": {k: round(sum(v) / len(v), 1) for k, v in durations.items()},
        "rejection_reasons": dict(Counter(a.rejection_reason for a in apps if a.rejection_reason)),
        "score_ranges": [
            {
                "label": f"{lo}–{hi}",
                "count": sum(j.score is not None and lo <= j.score <= hi for j in jobs),
            }
            for lo, hi in ((0, 39.9), (40, 59.9), (60, 79.9), (80, 100))
        ],
    }


def refresh_notifications(db, user_id):
    data = overview(db, user_id)
    items = [
        ("follow:" + f["id"], f"Acompanhe {f['company']}: {f['title']}", f["job_id"])
        for f in data["followups"]
    ]
    for i in data["upcoming"]:
        from datetime import datetime

        if datetime.fromisoformat(i["scheduled_at"].replace("Z", "")) <= now() + timedelta(days=1):
            items.append(
                (
                    "interview:" + i["id"],
                    f"Entrevista nas próximas 24 horas: {i['company']}",
                    i["job_id"],
                )
            )
    existing = set(db.scalars(select(Notification.key).where(Notification.user_id == user_id)))
    for key, title, job_id in items:
        if key not in existing:
            db.add(Notification(user_id=user_id, key=key, title=title, job_id=job_id))
    db.flush()


def usage_summary(db, user_id):
    rows = db.scalars(
        select(AIUsage).where(
            AIUsage.user_id == user_id, AIUsage.created_at >= now() - timedelta(days=30)
        )
    ).all()
    return {
        "calls": len(rows),
        "tokens": sum(r.tokens for r in rows),
        "failed": sum(r.status == "failed" for r in rows),
        "days": 30,
    }
