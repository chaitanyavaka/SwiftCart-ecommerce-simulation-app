from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "item"


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def serialize_document(document: dict | None) -> dict | None:
    if document is None:
        return None
    return serialize_value(document)


def collection_list(collection, query: dict | None = None, sort=None, limit: int = 0) -> list[dict]:
    return [serialize_document(item) for item in collection.find(query or {}, sort=sort, limit=limit)]


def format_money(value: Any) -> str:
    try:
        return f"Rs. {float(value):,.0f}"
    except (TypeError, ValueError):
        return "Rs. 0"


def format_number(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def format_datetime(value: Any) -> str:
    if not value:
        return "Never"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.astimezone(timezone.utc).strftime("%b %d, %H:%M UTC")


def get_simulation_config(db) -> dict:
    config = db["simulation_config"].find_one({"_id": "main"})
    if config:
        return serialize_document(config)
    return {
        "_id": "main",
        "running": False,
        "speed": "five_minute",
        "interval_seconds": 300,
        "max_discount_pct": 25,
        "tick_count": 0,
    }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
