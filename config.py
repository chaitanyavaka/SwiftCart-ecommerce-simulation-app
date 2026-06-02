"""Configuration for the standalone ecommerce simulation app."""

from __future__ import annotations

import os


def _load_local_env() -> None:
    for filename in (".env", ".env.local"):
        if not os.path.exists(filename):
            continue
        with open(filename, "r", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lstrip("\ufeff")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


_load_local_env()


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "demo-secret-change-me")

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "demo123")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "swiftcart_marketplace")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "20000"))
    USE_MEMORY_DB = _truthy(os.getenv("DEMO_USE_MEMORY_DB"), False)
    MONGO_FALLBACK_TO_MEMORY = _truthy(os.getenv("MONGO_FALLBACK_TO_MEMORY"), True)

    AUTO_SEED = _truthy(os.getenv("AUTO_SEED"), True)
    AUTO_START_SIMULATION = _truthy(os.getenv("AUTO_START_SIMULATION"), True)
    MAX_DISCOUNT_PCT = int(os.getenv("MAX_DISCOUNT_PCT", "25"))
    AGENT_INTERVAL_SECONDS = int(os.getenv("AGENT_INTERVAL_SECONDS", "300"))

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    SIMULATION_RANDOM_SEED = os.getenv("SIMULATION_RANDOM_SEED")
