from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import BACKEND_ROOT


@lru_cache
def expected_revision():
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()
