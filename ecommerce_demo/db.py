from __future__ import annotations

from typing import Any

from .memory_mongo import MemoryDatabase


def get_database(config: dict[str, Any]):
    if config.get("USE_MEMORY_DB"):
        return MemoryDatabase()

    try:
        from pymongo import MongoClient

        client = MongoClient(
            config["MONGO_URI"],
            serverSelectionTimeoutMS=int(config.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", 20000)),
            uuidRepresentation="standard",
        )
        client.admin.command("ping")
        return client[config["MONGO_DB_NAME"]]
    except Exception:
        if config.get("MONGO_FALLBACK_TO_MEMORY", True):
            return MemoryDatabase()
        raise
