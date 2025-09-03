from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    timezone: str


def _default_database_url() -> str:
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "worktime.db"
    # Async driver for SQLAlchemy + SQLite
    return f"sqlite+aiosqlite:///{db_path}"


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", _default_database_url()),
        timezone=os.getenv("TZ", "Europe/Moscow"),
    )



