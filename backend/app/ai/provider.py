import hashlib
import json
from pathlib import Path
from typing import Protocol, TypeVar

from fastapi import HTTPException
from openai import APIError, OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.config import settings
from app.models import AIUsage, Profile, now
from app.schemas import DNA, JobData, Schema, SkillInput

T = TypeVar("T", bound=BaseModel)
PROMPT_VERSION = "v1"
PROMPT = (Path(__file__).parent / "prompts" / "v1.txt").read_text(encoding="utf-8")


class ResumeExtraction(Schema):
    profile: DNA
    skills: list[SkillInput]
    warnings: list[str]


class Citation(Schema):
    source_id: str
    quote: str


class Advice(Schema):
    body: str = Field(min_length=1, max_length=20000)
    citations: list[Citation]
    missing_information: list[str]


class AIProvider(Protocol):
    def structured(self, instruction: str, context: dict, schema: type[T]) -> tuple[T, int]: ...


class OpenAIProvider:
    def structured(self, instruction: str, context: dict, schema: type[T]) -> tuple[T, int]:
        client = OpenAI(api_key=settings().openai_api_key, timeout=75, max_retries=1)
        response = client.responses.parse(
            model=settings().ai_model,
            store=False,
            input=[
                {"role": "system", "content": PROMPT + "\nTarefa: " + instruction},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            text_format=schema,
            max_output_tokens=6500,
        )
        if response.output_parsed is None:
            raise HTTPException(
                502, "O provedor não retornou uma resposta válida. Tente reduzir o texto."
            )
        return response.output_parsed, response.usage.total_tokens if response.usage else 0


def run_ai(db, user_id, kind, instruction, context, schema: type[T]) -> T:
    cfg = settings()
    if not cfg.openai_api_key:
        raise HTTPException(
            503,
            "IA não configurada. Defina OPENAI_API_KEY no arquivo .env da raiz e reinicie a API.",
        )
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if not profile or not profile.data.get("ai_consent"):
        raise HTTPException(
            403, "Autorize o envio do contexto profissional ao provedor em Career DNA."
        )
    packed = json.dumps(
        [kind, instruction, context, cfg.ai_model, PROMPT_VERSION],
        sort_keys=True,
        ensure_ascii=False,
    )
    cache_key = hashlib.sha256(packed.encode()).hexdigest()
    cached = db.scalar(
        select(AIUsage)
        .where(
            AIUsage.user_id == user_id,
            AIUsage.cache_key == cache_key,
            AIUsage.status == "completed",
        )
        .order_by(AIUsage.created_at.desc())
    )
    if cached:
        return schema.model_validate(cached.output)
    # Serialize reservations per user in PostgreSQL, so concurrent calls share a budget.
    db.scalar(select(Profile).where(Profile.user_id == user_id).with_for_update())
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(
        select(func.count())
        .select_from(AIUsage)
        .where(AIUsage.user_id == user_id, AIUsage.created_at >= today)
    )
    if count >= cfg.ai_daily_limit:
        raise HTTPException(
            429,
            "Limite diário de chamadas de IA atingido. Respostas em cache continuam disponíveis.",
        )
    running = db.scalar(
        select(AIUsage).where(
            AIUsage.user_id == user_id,
            AIUsage.cache_key == cache_key,
            AIUsage.status == "running",
            AIUsage.created_at
            >= now().replace(microsecond=0) - __import__("datetime").timedelta(minutes=3),
        )
    )
    if running:
        raise HTTPException(409, "Esta análise já está em andamento. Aguarde e tente novamente.")
    usage = AIUsage(
        user_id=user_id,
        kind=kind,
        model=cfg.ai_model,
        prompt_version=PROMPT_VERSION,
        cache_key=cache_key,
    )
    db.add(usage)
    db.commit()
    try:
        result, tokens = OpenAIProvider().structured(instruction, context, schema)
        if isinstance(result, Advice):
            sources = context.get("sources", {})
            if sources and not result.citations:
                raise ValueError("Resposta sem fontes")
            for citation in result.citations:
                source = sources.get(citation.source_id)
                if not source or not citation.quote or citation.quote not in source:
                    raise ValueError("Citação não sustentada pelo contexto")
        usage.output = result.model_dump(mode="json")
        usage.status = "completed"
        usage.tokens = tokens
        db.commit()
        return result
    except (APIError, ValueError, HTTPException) as exc:
        usage.status = "failed"
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            502,
            "A IA não concluiu uma resposta validada. Verifique a chave, o modelo ou tente novamente.",
        ) from exc


def parse_job(db, user_id, text):
    return run_ai(
        db,
        user_id,
        "parse_job",
        "Extraia os campos da vaga, sem preencher dados ausentes por suposição.",
        {"text": text},
        JobData,
    )


def parse_resume(db, user_id, text):
    return run_ai(
        db,
        user_id,
        "parse_resume",
        "Extraia o currículo. Não altere consentimento ou configurações. Skills são declarações, não evidências verificadas.",
        {"text": text},
        ResumeExtraction,
    )


def analyze_match(db, user_id, context):
    return run_ai(
        db,
        user_id,
        "analyze_match",
        "Explique a compatibilidade contextual e ambiguidades; não atribua score.",
        context,
        Advice,
    )


def generate_message(db, user_id, context):
    return run_ai(
        db,
        user_id,
        "generate_message",
        "Escreva um rascunho curto para recrutador, usando somente fatos citáveis do perfil.",
        context,
        Advice,
    )


def prepare_interview(db, user_id, context):
    return run_ai(
        db,
        user_id,
        "prepare_interview",
        "Prepare uma entrevista específica: tópicos, perguntas técnicas e comportamentais, perguntas STAR a preencher, projetos reais, gaps, perguntas ao entrevistador e checklist.",
        context,
        Advice,
    )


def career_coach(db, user_id, context):
    return run_ai(
        db,
        user_id,
        "career_coach",
        "Responda à pergunta usando apenas contexto disponível. Pode conduzir entrevista simulada com uma pergunta de cada vez.",
        context,
        Advice,
    )
