from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import SavedJobSearch, now
from app.schemas import SearchInput
from app.security import current_user, owned
from app.serializers import serialize
from app.services.scheduling import enqueue

router = APIRouter(tags=["searches"])


@router.get("/providers")
def providers(user=Depends(current_user)):
    return [
        {
            "id": "jooble",
            "configured": bool(settings().jooble_api_key),
            "region": settings().jooble_region,
        },
        {"id": "greenhouse", "configured": True},
        {"id": "lever", "configured": True},
    ]


@router.get("/saved-searches")
def listing(user=Depends(current_user), db: Session = Depends(get_db)):
    return [
        serialize(s)
        for s in db.scalars(
            select(SavedJobSearch)
            .where(SavedJobSearch.user_id == user.id)
            .order_by(SavedJobSearch.created_at.desc())
        )
    ]


@router.post("/saved-searches", status_code=201)
def create(body: SearchInput, user=Depends(current_user), db: Session = Depends(get_db)):
    search = SavedJobSearch(
        user_id=user.id,
        **body.model_dump(),
        next_run_at=now() if body.enabled and body.cadence_hours else None,
    )
    db.add(search)
    db.flush()
    return serialize(search)


@router.put("/saved-searches/{search_id}")
def edit(
    search_id: str, body: SearchInput, user=Depends(current_user), db: Session = Depends(get_db)
):
    search = owned(db, SavedJobSearch, search_id, user.id)
    for k, v in body.model_dump().items():
        setattr(search, k, v)
    search.updated_at = now()
    search.next_run_at = (
        now() + timedelta(hours=body.cadence_hours) if body.enabled and body.cadence_hours else None
    )
    return serialize(search)


@router.delete("/saved-searches/{search_id}")
def remove(search_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned(db, SavedJobSearch, search_id, user.id))
    return {"deleted": True}


@router.post("/saved-searches/{search_id}/run", status_code=202)
def run(search_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    search = db.scalar(
        select(SavedJobSearch)
        .where(SavedJobSearch.id == search_id, SavedJobSearch.user_id == user.id)
        .with_for_update()
    )
    if not search:
        raise HTTPException(404, "Busca não encontrada.")
    if not search.enabled:
        raise HTTPException(409, "Ative a busca para executar.")
    return serialize(enqueue(db, search))
