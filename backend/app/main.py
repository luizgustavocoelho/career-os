import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api import applications, auth, documents, insights, jobs, profile, searches
from app.config import settings
from app.db import SessionLocal
from app.services.health import expected_revision

log = logging.getLogger("careeros")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app):
    settings().validate_production()
    yield


app = FastAPI(
    title="CareerOS API",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings().environment != "production" else None,
)
origins = {s.strip() for s in settings().allowed_origins.split(",")} | {settings().app_origin}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.monotonic()
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in origins:
        return JSONResponse(
            {"detail": "Origem não autorizada.", "request_id": request_id}, status_code=403
        )
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        return JSONResponse({"detail": "Content-Length inválido."}, status_code=400)
    if length > (settings().upload_max_mb + 1) * 1024 * 1024:
        return JSONResponse({"detail": "Requisição excedeu o limite de tamanho."}, status_code=413)
    try:
        response = await call_next(request)
    except Exception as exc:
        log.error(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                }
            )
        )
        response = JSONResponse(
            {
                "detail": "Não foi possível concluir. Tente novamente e informe o código de atendimento se persistir.",
                "request_id": request_id,
            },
            status_code=500,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    log.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "detail": "Revise os campos informados.",
            "errors": [
                {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                for e in exc.errors()
            ],
        },
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        {"detail": "Registro duplicado ou alterado simultaneamente. Atualize e tente novamente."},
        status_code=409,
    )


@app.get("/api/health")
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision != expected_revision():
                raise RuntimeError("Migrations pending")
        return {"status": "ok", "database": "ok"}
    except Exception:
        return JSONResponse(
            {"status": "unavailable", "detail": "Banco indisponível ou migrations pendentes."},
            status_code=503,
        )


for router in (
    auth.router,
    profile.router,
    documents.router,
    jobs.router,
    applications.router,
    insights.router,
    searches.router,
):
    app.include_router(router, prefix="/api")
