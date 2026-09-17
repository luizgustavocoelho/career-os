"""Only official public APIs are fetched. No arbitrary URL fetching or redirects."""

import base64
import re
from typing import Protocol
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.domain.parsers import local_job
from app.schemas import JobData

ALLOWED_HOSTS = {"boards-api.greenhouse.io", "api.lever.co", "api.github.com"}


def public_json(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.port not in (None, 443)
    ):
        raise HTTPException(422, "Fonte não permitida.")
    try:
        with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
            with client.stream(
                "GET", url, headers={"Accept": "application/json", "User-Agent": "CareerOS/1.0"}
            ) as response:
                response.raise_for_status()
                if response.status_code != 200:
                    raise HTTPException(502, "A fonte retornou um redirecionamento não permitido.")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 5_000_000:
                        raise HTTPException(422, "Resposta da fonte excedeu o limite de tamanho.")
                import json

                return json.loads(data)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            502,
            "Não foi possível consultar a fonte pública. Confira o endereço ou cole a descrição.",
        ) from exc


def plain(html):
    return BeautifulSoup(html or "", "html.parser").get_text("\n", strip=True)


class JobProvider(Protocol):
    def list_jobs(self, board: str) -> list[JobData]: ...


class Greenhouse:
    def list_jobs(self, board):
        data = public_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
        return [
            local_job(
                plain(j.get("content"))[:60000],
                title=j["title"],
                company=board,
                location=j.get("location", {}).get("name", ""),
                url=j.get("absolute_url"),
                source=f"greenhouse:{board}",
                external_id=str(j["id"]),
            )
            for j in data.get("jobs", [])[:500]
            if len(plain(j.get("content"))) >= 20
        ]


class Lever:
    def list_jobs(self, board):
        data = public_json(f"https://api.lever.co/v0/postings/{board}?mode=json&limit=100")
        result = []
        for j in data:
            text = (
                plain(j.get("description", ""))
                + "\n"
                + "\n".join(plain(x.get("content", "")) for x in j.get("lists", []))
            )
            if len(text) >= 20:
                result.append(
                    local_job(
                        text[:60000],
                        title=j["text"],
                        company=board,
                        location=j.get("categories", {}).get("location", ""),
                        url=j.get("hostedUrl"),
                        source=f"lever:{board}",
                        external_id=j["id"],
                    )
                )
        return result


PROVIDERS = {"greenhouse": Greenhouse(), "lever": Lever()}


def from_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.password:
        raise HTTPException(422, "Use uma URL HTTPS pública de vaga.")
    segments = parts.path.strip("/").split("/")
    board, job_id, provider = "", "", ""
    if (
        parts.hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"}
        and len(segments) >= 3
        and segments[1] == "jobs"
    ):
        board, job_id, provider = segments[0], segments[2], "greenhouse"
    elif parts.hostname == "jobs.lever.co" and len(segments) >= 2:
        board, job_id, provider = segments[0], segments[1], "lever"
    elif parts.hostname == "boards.greenhouse.io" and segments == ["embed", "job_app"]:
        query = parse_qs(parts.query)
        board, job_id, provider = (
            query.get("for", [""])[0],
            query.get("token", [""])[0],
            "greenhouse",
        )
    if (
        not provider
        or not re.fullmatch(r"[A-Za-z0-9_-]+", board)
        or not re.fullmatch(r"[A-Za-z0-9_-]+", job_id)
    ):
        raise HTTPException(
            422,
            "Importação automática por URL suporta Greenhouse e Lever. Para outras fontes, cole a descrição e mantenha o link original.",
        )
    if provider == "greenhouse":
        j = public_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}")
        return local_job(
            plain(j.get("content"))[:60000],
            title=j["title"],
            company=board,
            location=j.get("location", {}).get("name", ""),
            url=url,
            source=f"greenhouse:{board}",
            external_id=job_id,
        )
    j = public_json(f"https://api.lever.co/v0/postings/{board}/{job_id}")
    text = (
        plain(j.get("description", ""))
        + "\n"
        + "\n".join(plain(x.get("content", "")) for x in j.get("lists", []))
    )
    return local_job(
        text[:60000],
        title=j["text"],
        company=board,
        location=j.get("categories", {}).get("location", ""),
        url=url,
        source=f"lever:{board}",
        external_id=job_id,
    )


def github_project(url):
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    if (
        parts.scheme != "https"
        or parts.hostname != "github.com"
        or len(segments) != 2
        or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in segments)
    ):
        raise HTTPException(
            422, "Informe https://github.com/usuario/repositorio de um repositório público."
        )
    root = "https://api.github.com/repos/" + "/".join(segments)
    repo = public_json(root)
    languages = public_json(root + "/languages")
    try:
        readme = public_json(root + "/readme")
        text = base64.b64decode(readme.get("content", "")).decode("utf-8", errors="replace")[:12000]
    except HTTPException:
        text = ""
    return {
        "title": repo["name"],
        "url": repo["html_url"],
        "description": repo.get("description") or "",
        "languages": list(languages),
        "readme": text,
        "warning": "Linguagens são indícios. Confirme sua contribuição e descreva o que fez antes de registrar evidência.",
    }
