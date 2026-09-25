"""Official Jooble search API. Fixed regional hosts, bounded requests, no scraping."""

import json
import logging
import time
from collections.abc import Iterator
from datetime import timedelta
from typing import Protocol
from urllib.parse import quote

import httpx
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.domain.parsers import local_job
from app.integrations.jobs import plain
from app.models import RateLimit, now
from app.schemas import JobData


class SearchJobProvider(Protocol):
    """Search-capable adapter, alongside the existing board-based JobProvider."""

    def search(self, search) -> Iterator[JobData]: ...


# HTTP request URLs contain the key; never allow the HTTP client to log URLs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class ProviderError(RuntimeError):
    def __init__(
        self,
        message="Falha na API Jooble. Verifique a chave regional e a conexão.",
        retry_seconds=900,
    ):
        super().__init__(message)
        self.retry_seconds = retry_seconds


def reserve_request():
    """Global account budget survives restart; conservative limits, also for manual runs."""
    with SessionLocal() as db:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(1667330660)"))
        else:
            db.execute(text("BEGIN IMMEDIATE"))
        for period, seconds, limit in (
            ("minute", 60, 10),
            ("day", 86400, 100),
            ("month", 2592000, 2000),
        ):
            key = "provider:jooble:" + period
            row = db.get(RateLimit, key)
            if row is None:
                row = RateLimit(key=key, count=0, reset_at=now() + timedelta(seconds=seconds))
                db.add(row)
            elif row.reset_at <= now():
                row.count, row.reset_at = 0, now() + timedelta(seconds=seconds)
            if row.count >= limit:
                raise ProviderError(
                    "Limite local de chamadas Jooble atingido. Aguarde a próxima janela.",
                    max(60, int((row.reset_at - now()).total_seconds())),
                )
            row.count += 1
        db.commit()


def request_page(keywords, location, page, salary_min=None):
    cfg = settings()
    if not cfg.jooble_api_key:
        raise ProviderError(
            "Jooble não configurado. Defina JOOBLE_API_KEY para a região selecionada."
        )
    reserve_request()
    host = {"br": "br.jooble.org", "us": "jooble.org", "pt": "pt.jooble.org"}[cfg.jooble_region]
    body = {"keywords": keywords, "location": location, "page": page, "ResultOnPage": 20}
    # Salary is deliberately not sent: API salary period/currency isn't unambiguous.
    try:
        with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "POST", f"https://{host}/api/{quote(cfg.jooble_api_key, safe='')}", json=body
            ) as response:
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "900")
                    raise ProviderError(
                        "Jooble limitou as chamadas. Nova tentativa após espera.",
                        max(900, min(int(retry) if retry.isdigit() else 900, 2592000)),
                    )
                if response.status_code != 200:
                    raise ProviderError()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 5_000_000:
                        raise ProviderError("Resposta Jooble excedeu o limite de tamanho.")
                return json.loads(data)
    except (httpx.HTTPError, ValueError):
        raise ProviderError() from None


class Jooble:
    def search(self, search):
        for term in search.keywords:
            for page in (1, 2):
                payload = request_page(term, search.location, page)
                rows = payload.get("jobs", [])
                if not isinstance(rows, list):
                    raise ProviderError("Formato inesperado da API Jooble.")
                for row in rows[:20]:
                    description = plain(row.get("snippet"))[:60000]
                    if not row.get("title") or not row.get("company") or len(description) < 20:
                        continue
                    # type is employment contract, not work mode. updated is not publication date.
                    yield local_job(
                        description,
                        title=plain(row["title"])[:240],
                        company=plain(row["company"])[:240],
                        location=plain(row.get("location"))[:240],
                        url=row.get("link"),
                        source="jooble",
                        salary_currency="",
                        salary_period="unknown",
                        external_id=str(row["id"])[:160],
                    )
                if len(rows) < 20:
                    break
                time.sleep(6)


SEARCH_PROVIDERS = {"jooble": Jooble()}
