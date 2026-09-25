from pathlib import Path

import pytest

from app.config import BACKEND_ROOT, PROJECT_ROOT, Settings


@pytest.mark.parametrize(
    "directory", [PROJECT_ROOT, BACKEND_ROOT, PROJECT_ROOT / "scripts", BACKEND_ROOT / "app"]
)
def test_settings_independent_of_cwd(monkeypatch, tmp_path, directory):
    env = tmp_path / ".env"
    env.write_text(
        "APP_ORIGIN=https://fixture.example\nALLOWED_ORIGINS=https://fixture.example\nDATABASE_URL=sqlite:///./data/fixture.db\n",
        encoding="utf-8",
    )
    for key in ("APP_ORIGIN", "ALLOWED_ORIGINS", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(directory)
    cfg = Settings(_env_file=env)
    assert cfg.app_origin == "https://fixture.example"
    assert cfg.allowed_origins == "https://fixture.example"
    assert Path(cfg.model_config["env_file"]) == PROJECT_ROOT / ".env"
    assert str(BACKEND_ROOT / "data" / "fixture.db") in cfg.database_url
    assert cfg.data_dir.is_absolute()


def test_environment_override_and_memory_database(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("APP_ORIGIN=https://file.example", encoding="utf-8")
    monkeypatch.setenv("APP_ORIGIN", "https://override.example")
    cfg = Settings(_env_file=env, database_url="sqlite:///:memory:")
    assert cfg.app_origin == "https://override.example"
    assert cfg.database_url == "sqlite:///:memory:"
