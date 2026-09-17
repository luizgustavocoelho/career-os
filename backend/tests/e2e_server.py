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

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

command.upgrade(Config("alembic.ini"), "head")
uvicorn.run("app.main:app", host="127.0.0.1", port=8011)
