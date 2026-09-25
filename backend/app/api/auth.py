from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Profile, User
from app.schemas import DNA, AuthInput
from app.security import (
    COOKIE,
    DUMMY_HASH,
    check_password,
    create_session,
    current_user,
    hasher,
    throttle,
    user_count,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
def config(db: Session = Depends(get_db, scope="function")):
    cfg = settings()
    return {
        "registration_open": cfg.registration_enabled
        and (cfg.registration_limit == 0 or user_count(db) < cfg.registration_limit)
    }


@router.post("/register", status_code=201)
def register(
    body: AuthInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
):
    throttle(db, "register:" + (request.client.host if request.client else "local"), 5)
    cfg = settings()
    if cfg.registration_limit:
        # Serialize the count-and-create boundary, including multiple API processes.
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(1667330655)"))
        else:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    if not cfg.registration_enabled or (
        cfg.registration_limit and user_count(db) >= cfg.registration_limit
    ):
        raise HTTPException(403, "Cadastro fechado nesta instalação. Entre na conta existente.")
    email = str(body.email).lower()
    if not body.name.strip():
        raise HTTPException(422, "Informe seu nome.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Não foi possível criar a conta com este e-mail.")
    user = User(email=email, name=body.name.strip(), password_hash=hasher.hash(body.password))
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, data=DNA(name=user.name, email=user.email).model_dump()))
    return create_session(db, user, response)


@router.post("/login")
def login(
    body: AuthInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
):
    ip = request.client.host if request.client else "local"
    throttle(db, "login-ip:" + ip, 30)
    throttle(db, "login-email:" + str(body.email).lower(), 10)
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    encoded = user.password_hash if user else DUMMY_HASH
    valid = check_password(encoded, body.password)
    if not user or not valid:
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return create_session(db, user, response)


@router.get("/me")
def me(request: Request, user=Depends(current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "csrf_token": request.state.session.csrf_token,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user=Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    db.delete(request.state.session)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
