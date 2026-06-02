from __future__ import annotations

from flask import Flask

from config import Config

from .agents import SimulationEngine
from .db import get_database
from .metrics import get_business_metrics
from .routes.api import api_bp
from .routes.assets import assets_bp
from .routes.auth import auth_bp
from .routes.views import views_bp
from .seed import DATASET_VERSION, seed_demo_data
from .utils import format_datetime, format_money, format_number, get_simulation_config


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    db = get_database(app.config)
    app.extensions["demo_db"] = db

    config_document = db["simulation_config"].find_one({"_id": "main"})
    dataset_is_current = config_document and config_document.get("dataset_version") == DATASET_VERSION
    if app.config.get("AUTO_SEED", True) and (
        db["products"].count_documents({}) == 0 or not dataset_is_current
    ):
        seed_demo_data(db, max_discount_pct=app.config["MAX_DISCOUNT_PCT"])

    groq_api_key = app.config.get("GROQ_API_KEY")
    if app.config.get("TESTING") and not app.config.get("ENABLE_GROQ_IN_TESTS"):
        groq_api_key = None

    app.extensions["simulation_engine"] = SimulationEngine(
        db=db,
        groq_api_key=groq_api_key,
        groq_model=app.config.get("GROQ_MODEL"),
        random_seed=app.config.get("SIMULATION_RANDOM_SEED"),
        interval_seconds=app.config.get("AGENT_INTERVAL_SECONDS", 300),
    )
    if not app.config.get("TESTING") and app.config.get("AUTO_START_SIMULATION", True):
        app.extensions["simulation_engine"].start()

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(assets_bp)

    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["number"] = format_number
    app.jinja_env.filters["datetime"] = format_datetime

    @app.context_processor
    def inject_demo_context() -> dict:
        return {
            "business_metrics": get_business_metrics(db),
            "simulation_config": get_simulation_config(db),
        }

    return app
