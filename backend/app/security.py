import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import RateLimit, SessionToken, User, now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
COOKIE = "careeros_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def check_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except VerificationError:
        return False


def throttle(db: Session, key: str, limit: int = 10, minutes: int = 15):
    key = digest(key)
    row = db.get(RateLimit, key)
    if row and row.reset_at <= now():
        db.delete(row)
        db.flush()
        row = None
    if not row:
        row = RateLimit(key=key, count=0, reset_at=now() + timedelta(minutes=minutes))
        db.add(row)
        db.flush()
    changed = db.execute(
        update(RateLimit)
        .where(RateLimit.key == key, RateLimit.count < limit)
        .values(count=RateLimit.count + 1)
    ).rowcount
    db.commit()  # Failed requests must still consume their rate limit.
    if not changed:
        raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos.")


def create_session(db: Session, user: User, response: Response):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.execute(delete(SessionToken).where(SessionToken.expires_at < now()))
    db.add(
        SessionToken(
            user_id=user.id,
            token_hash=digest(token),
            csrf_token=csrf,
            expires_at=now() + timedelta(days=settings().session_days),
        )
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        max_age=settings().session_days * 86400,
        path="/",
    )
    return {"id": user.id, "name": user.name, "email": user.email, "csrf_token": csrf}


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE, "")
    session = db.scalar(
        select(SessionToken).where(
            SessionToken.token_hash == digest(token), SessionToken.expires_at > now()
        )
    )
    if not session:
        raise HTTPException(401, "Entre na sua conta para continuar.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, "Sessão inválida. Atualize a página.")
    request.state.session = session
    return db.get(User, session.user_id)


def owned(db: Session, model, record_id: str, user_id: str):
    obj = db.scalar(select(model).where(model.id == record_id, model.user_id == user_id))
    if obj is None:
        raise HTTPException(404, "Registro não encontrado.")
    return obj


def user_count(db):
    return db.scalar(select(func.count()).select_from(User))
