"""Create an isolated, migrated database for the browser test. Never touches the user's DB."""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///./data/e2e-" + uuid.uuid4().hex + ".db"
os.environ["REGISTRATION_LIMIT"] = "0"
os.environ["APP_ORIGIN"] = "http://127.0.0.1:3011"
os.environ["ALLOWED_ORIGINS"] = "http://127.0.0.1:3011"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ENVIRONMENT"] = "test"
os.environ["REGISTRATION_ENABLED"] = "true"
os.environ["COOKIE_SECURE"] = "false"
os.environ["JOOBLE_API_KEY"] = ""

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

command.upgrade(Config("alembic.ini"), "head")
# Fake exists only in the isolated test harness, never in application startup.
import threading  # noqa: E402

from app import worker  # noqa: E402
from app.schemas import JobData  # noqa: E402


class FixtureProvider:
    def search(self, search):
        yield JobData(
            title="Engenheiro de Dados Fixture",
            company="Empresa Radar E2E",
            location="São Paulo",
            description="Construir pipelines de dados com Python e SQL em projetos reais.",
            source="jooble",
            external_id="test-1",
            requirements=[{"skill": "Python", "mandatory": True}],
            work_model="remote",
            seniority="junior",
        )


worker.SEARCH_PROVIDERS["jooble"] = FixtureProvider()
threading.Thread(target=worker.main, daemon=True).start()
uvicorn.run("app.main:app", host="127.0.0.1", port=8011)
