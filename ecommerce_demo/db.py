from __future__ import annotations

from typing import Any

from .memory_mongo import MemoryDatabase


def get_database(config: dict[str, Any]):
    # Use in-memory database if explicitly enabled
    if config.get("USE_MEMORY_DB"):
        return MemoryDatabase()

    try:
        from pymongo import MongoClient
        import certifi

        client = MongoClient(
            config["MONGO_URI"],
            serverSelectionTimeoutMS=int(
                config.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", 20000)
            ),
            uuidRepresentation="standard",
            tls=True,
            tlsCAFile=certifi.where(),
            retryWrites=True,
        )

        # Verify connection
        client.admin.command("ping")

        print("✅ MongoDB connection successful")

        return client[config["MONGO_DB_NAME"]]

    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

        if config.get("MONGO_FALLBACK_TO_MEMORY", True):
            print("⚠️ Falling back to MemoryDatabase")
            return MemoryDatabase()

        raise