"""Conservative local extraction. It never claims semantic understanding or invents missing fields."""

import re
from io import BytesIO

from fastapi import HTTPException
from pypdf import PdfReader

from app.domain.skills import ALIASES, normalize
from app.schemas import DNA, JobData, Requirement, SkillInput

KNOWN = {
    "python",
    "sql",
    "postgresql",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "aws",
    "azure",
    "gcp",
    "airflow",
    "spark",
    "etl",
    "docker",
    "kubernetes",
    "git",
    "java",
    "c#",
    "c++",
    "excel",
    "power bi",
    "fastapi",
    "django",
    "pandas",
    "numpy",
    "linux",
    "terraform",
    "dbt",
    "snowflake",
    "tableau",
    "go",
    "rust",
    "redis",
    "mongodb",
    "kafka",
    "next.js",
}


def extract_skills(text):
    normalized = normalize(text)
    result = set()
    for word in KNOWN | set(ALIASES):
        if re.search(r"(?<![\w])" + re.escape(word) + r"(?![\w])", normalized):
            result.add(normalize(word))
    return sorted(result)


def local_job(text, title="Revisar cargo", company="Revisar empresa", **kwargs):
    requirements = []
    for skill in extract_skills(text):
        sentences = re.split(r"[\n;]+|(?<=[.!?])\s+", text)
        lines = [line.strip() for line in sentences if skill in extract_skills(line)]
        line = lines[0] if lines else skill
        optional = any(
            w in normalize(line) for w in ("desejavel", "diferencial", "nice to have", "preferred")
        )
        requirements.append(
            Requirement(skill=skill, mandatory=not optional, description=line[:2000])
        )
    return JobData(
        title=title, company=company, description=text, requirements=requirements, **kwargs
    )


def pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(422, "O arquivo não é um PDF válido.")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "Remova a senha do PDF antes do upload.")
        if len(reader.pages) > 40:
            raise HTTPException(422, "O currículo deve ter no máximo 40 páginas.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if len(text) > 60000:
            raise HTTPException(422, "PDF muito extenso. Limite de 60 mil caracteres.")
        return text.strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            422, "Não foi possível ler este PDF. Exporte novamente como PDF de texto."
        ) from exc


def local_resume(text):
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "profile": DNA(
            name=lines[0][:160] if lines else "", email=email.group(0) if email else ""
        ).model_dump(),
        "skills": [SkillInput(name=s).model_dump() for s in extract_skills(text)],
        "warnings": [
            "Extração local: nome, e-mail e termos de habilidades. Revise tudo. Use extração com IA para estruturar experiências e formação."
        ],
    }
