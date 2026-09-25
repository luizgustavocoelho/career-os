from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import parse_resume
from app.config import settings
from app.db import get_db
from app.domain.parsers import local_resume, pdf_text
from app.models import Application, Document, Job
from app.schemas import DocumentInput
from app.security import current_user, owned
from app.serializers import serialize

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def listing(user=Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return [
        {
            **serialize(d, exclude=("text", "extracted")),
            "applications": references(db, user.id, d.id),
        }
        for d in db.scalars(
            select(Document)
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc())
            .limit(200)
        )
    ]


@router.post("/upload", status_code=201)
def upload(
    file: UploadFile = File(...),
    user=Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    limit = settings().upload_max_mb * 1024 * 1024
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"O arquivo deve ter até {settings().upload_max_mb} MB.")
    text = pdf_text(content)
    extracted = local_resume(text)
    if not text:
        extracted["warnings"] = [
            "Este PDF não contém texto extraível. Cole o texto ou envie uma versão pesquisável. OCR não está habilitado."
        ]
    doc = Document(
        user_id=user.id,
        name=(file.filename or "Currículo.pdf")[:240],
        kind="resume",
        content_type="application/pdf",
        content=content,
        text=text,
        extracted=extracted,
    )
    db.add(doc)
    db.flush()
    return serialize(doc)


@router.post("", status_code=201)
def create(
    body: DocumentInput, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    if body.parent_id:
        owned(db, Document, body.parent_id, user.id)
    doc = Document(user_id=user.id, **body.model_dump())
    db.add(doc)
    db.flush()
    return serialize(doc)


@router.get("/{document_id}")
def detail(
    document_id: str, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    return {
        **serialize(owned(db, Document, document_id, user.id)),
        "applications": references(db, user.id, document_id),
    }


def references(db, user_id, document_id):
    return [
        {"id": a.id, "job_id": a.job_id, "title": j.title}
        for a, j in db.execute(
            select(Application, Job)
            .join(Job, Job.id == Application.job_id)
            .where(Application.user_id == user_id, Application.resume_id == document_id)
        )
    ]


@router.delete("/{document_id}")
def remove(
    document_id: str, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    doc = owned(db, Document, document_id, user.id)
    if references(db, user.id, doc.id) or db.scalar(
        select(Document.id).where(Document.parent_id == doc.id)
    ):
        raise HTTPException(
            409, "Documento vinculado a candidatura ou versão derivada. Preserve o histórico."
        )
    db.delete(doc)
    return {"deleted": True}


@router.post("/{document_id}/extract")
def extract(
    document_id: str, user=Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    doc = owned(db, Document, document_id, user.id)
    if len(doc.text) < 20:
        raise HTTPException(422, "O documento não contém texto suficiente para extração.")
    extracted = parse_resume(db, user.id, doc.text).model_dump()
    # Consent/settings are exclusively controlled by the user, never the model.
    extracted["profile"]["ai_consent"] = False
    doc.extracted = extracted
    return serialize(doc)


@router.get("/{document_id}/download")
def download(
    document_id: str,
    format: str = "original",
    user=Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    from urllib.parse import quote

    doc = owned(db, Document, document_id, user.id)
    if format in {"docx", "html"}:
        from app.services.document_formats import resume_docx, resume_html

        content = resume_docx(doc.text) if format == "docx" else resume_html(doc.text)
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if format == "docx"
            else "text/html; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''"
                + quote(doc.name + "." + format, safe=""),
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "Cache-Control": "no-store",
            },
        )
    if format != "original":
        raise HTTPException(422, "Formato suportado: original, docx ou html.")
    filename = doc.name if doc.content else doc.name.removesuffix(".pdf") + ".txt"
    return Response(
        content=doc.content if doc.content else doc.text.encode("utf-8"),
        media_type=doc.content_type,
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename, safe=""),
            "X-Content-Type-Options": "nosniff",
        },
    )
