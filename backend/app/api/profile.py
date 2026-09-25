from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.skills import normalize
from app.integrations.jobs import github_project
from app.models import Evidence, Job, Profile, ProfileSkill, Task
from app.schemas import EvidenceInput, ProfileUpdate, SkillInput, UrlInput
from app.security import current_user, owned
from app.serializers import serialize
from app.services.career import get_profile, skill_list

router = APIRouter(tags=["profile"])


def invalidate(db, user_id):
    db.execute(
        update(Job)
        .where(Job.user_id == user_id)
        .values(score=None, classification=None, coverage=None)
    )
    pending = db.scalar(
        select(Task).where(
            Task.user_id == user_id, Task.kind == "recalculate", Task.status == "pending"
        )
    )
    if not pending:
        db.add(Task(user_id=user_id, kind="recalculate"))


@router.get("/profile")
def get(user=Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return {**serialize(get_profile(db, user)), "skills": skill_list(db, user.id)}


@router.put("/profile")
def put(
    body: ProfileUpdate, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    profile = get_profile(db, user)
    changed = db.execute(
        update(Profile)
        .where(Profile.id == profile.id, Profile.version == body.version)
        .values(data=body.data.model_dump(), version=body.version + 1)
    ).rowcount
    if not changed:
        raise HTTPException(
            409, "Perfil alterado em outra janela. Atualize para evitar perder alterações."
        )
    invalidate(db, user.id)
    db.refresh(profile)
    return {**serialize(profile), "skills": skill_list(db, user.id)}


@router.post("/profile/skills", status_code=201)
def add_skill(
    body: SkillInput, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    normalized = normalize(body.name)
    skill = db.scalar(
        select(ProfileSkill).where(
            ProfileSkill.user_id == user.id, ProfileSkill.normalized == normalized
        )
    )
    if skill:
        raise HTTPException(409, "Essa habilidade já está cadastrada.")
    skill = ProfileSkill(user_id=user.id, normalized=normalized, **body.model_dump())
    db.add(skill)
    db.flush()
    invalidate(db, user.id)
    return serialize(skill)


@router.put("/profile/skills/{skill_id}")
def edit_skill(
    skill_id: str,
    body: SkillInput,
    user=Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    skill = owned(db, ProfileSkill, skill_id, user.id)
    for key, value in body.model_dump().items():
        setattr(skill, key, value)
    skill.normalized = normalize(body.name)
    invalidate(db, user.id)
    return serialize(skill)


@router.delete("/profile/skills/{skill_id}")
def delete_skill(
    skill_id: str, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    db.delete(owned(db, ProfileSkill, skill_id, user.id))
    invalidate(db, user.id)
    return {"ok": True}


@router.post("/profile/skills/{skill_id}/evidence", status_code=201)
def evidence(
    skill_id: str,
    body: EvidenceInput,
    user=Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    owned(db, ProfileSkill, skill_id, user.id)
    item = Evidence(user_id=user.id, skill_id=skill_id, **body.model_dump())
    db.add(item)
    db.flush()
    invalidate(db, user.id)
    return serialize(item)


@router.delete("/profile/evidence/{evidence_id}")
def delete_evidence(
    evidence_id: str, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    db.delete(owned(db, Evidence, evidence_id, user.id))
    invalidate(db, user.id)
    return {"ok": True}


@router.post("/integrations/github")
def github(body: UrlInput, user=Depends(current_user)):
    return github_project(body.url)
