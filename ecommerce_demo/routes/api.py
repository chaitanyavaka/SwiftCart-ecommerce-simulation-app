from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .auth import login_required
from ..metrics import get_business_metrics
from ..utils import collection_list, serialize_document


api_bp = Blueprint("api", __name__, url_prefix="/api")


def db():
    return current_app.extensions["demo_db"]


def engine():
    return current_app.extensions["simulation_engine"]


@api_bp.get("/products")
@login_required
def api_products():
    return jsonify(collection_list(db()["products"], sort=[("category", 1), ("name", 1)]))


@api_bp.get("/buyers")
@login_required
def api_buyers():
    return jsonify(collection_list(db()["buyers"], sort=[("lifetime_value", -1)]))


@api_bp.get("/sellers")
@login_required
def api_sellers():
    return jsonify(collection_list(db()["sellers"], sort=[("revenue", -1)]))


@api_bp.get("/transactions")
@login_required
def api_transactions():
    return jsonify(collection_list(db()["transactions"], sort=[("timestamp", -1)], limit=150))


@api_bp.get("/cashpoints")
@login_required
def api_cashpoints():
    database = db()
    return jsonify(
        {
            "ledger": collection_list(database["cashpoints_ledger"], sort=[("timestamp", -1)], limit=150),
            "balances": collection_list(database["buyers"], sort=[("cashpoints_balance", -1)], limit=25),
        }
    )


@api_bp.get("/metrics")
@login_required
def api_metrics():
    return jsonify(get_business_metrics(db()))


@api_bp.get("/agent-activity")
@login_required
def api_agent_activity():
    return jsonify(collection_list(db()["agent_activity_log"], sort=[("timestamp", -1)], limit=150))


@api_bp.post("/admin/simulation/start")
@login_required
def api_simulation_start():
    return jsonify(serialize_document(engine().start()))


@api_bp.post("/admin/simulation/stop")
@login_required
def api_simulation_stop():
    return jsonify(serialize_document(engine().stop()))


@api_bp.post("/admin/simulation/reset")
@login_required
def api_simulation_reset():
    return jsonify(serialize_document(engine().reset_demo_data(current_app.config["MAX_DISCOUNT_PCT"])))


@api_bp.post("/admin/simulation/speed")
@login_required
def api_simulation_speed():
    payload = request.get_json(silent=True) or request.form
    speed = payload.get("speed", "five_minute")
    return jsonify(serialize_document(engine().set_speed(speed)))
