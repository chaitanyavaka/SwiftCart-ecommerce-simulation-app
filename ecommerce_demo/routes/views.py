from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, session, url_for

from .auth import login_required
from ..metrics import get_business_metrics


views_bp = Blueprint("views", __name__)


def db():
    return current_app.extensions["demo_db"]


def _category_activity(products: list[dict]) -> list[dict]:
    categories: dict[str, dict] = {}
    for product in products:
        category = product.get("category", "Other")
        stats = categories.setdefault(
            category,
            {
                "category": category,
                "product_count": 0,
                "views_count": 0,
                "carts_count": 0,
                "sold_count": 0,
                "stock": 0,
                "discounted_count": 0,
                "low_stock_count": 0,
            },
        )
        stats["product_count"] += 1
        stats["views_count"] += int(product.get("views_count", 0))
        stats["carts_count"] += int(product.get("carts_count", 0))
        stats["sold_count"] += int(product.get("sold_count", 0))
        stats["stock"] += max(0, int(product.get("stock", 0)))
        stats["discounted_count"] += 1 if int(product.get("discount_pct", 0)) > 0 else 0
        stats["low_stock_count"] += 1 if product.get("status") == "Low Stock" else 0

    category_counts = []
    for stats in categories.values():
        live_activity = stats["views_count"] + (stats["carts_count"] * 2) + (stats["sold_count"] * 3)
        category_counts.append(
            {
                **stats,
                "count": live_activity,
                "label": "shopper actions",
                "secondary_count": stats["stock"],
                "secondary_label": "units live",
            }
        )
    return sorted(category_counts, key=lambda item: item["category"])


@views_bp.route("/")
def index():
    if session.get("admin_logged_in"):
        return redirect(url_for("views.dashboard"))
    return redirect(url_for("auth.login"))


@views_bp.route("/dashboard")
@login_required
def dashboard():
    database = db()
    metrics = get_business_metrics(database)
    recent_transactions = list(database["transactions"].find({}, sort=[("timestamp", -1)], limit=8))
    recent_logs = list(database["agent_activity_log"].find({}, sort=[("timestamp", -1)], limit=8))
    low_stock = list(database["products"].find({"status": "Low Stock"}, sort=[("stock", 1)], limit=6))
    products = list(database["products"].find({}))
    top_products = sorted(products, key=lambda product: product.get("sold_count", 0), reverse=True)[:12]
    category_counts = _category_activity(products)
    return render_template(
        "dashboard.html",
        page="dashboard",
        metrics=metrics,
        recent_transactions=recent_transactions,
        recent_logs=recent_logs,
        low_stock=low_stock,
        top_products=top_products,
        category_counts=category_counts,
    )


@views_bp.route("/products")
@login_required
def products():
    product_list = list(db()["products"].find({}, sort=[("category", 1), ("name", 1)]))
    return render_template("products.html", page="products", products=product_list)


@views_bp.route("/buyers")
@login_required
def buyers():
    buyer_list = list(db()["buyers"].find({}, sort=[("lifetime_value", -1)]))
    return render_template("buyers.html", page="buyers", buyers=buyer_list)


@views_bp.route("/sellers")
@login_required
def sellers():
    seller_list = list(db()["sellers"].find({}, sort=[("revenue", -1)]))
    return render_template("sellers.html", page="sellers", sellers=seller_list)


@views_bp.route("/point-of-sale")
@login_required
def point_of_sale():
    database = db()
    terminals = list(database["pos_terminals"].find({}, sort=[("store_name", 1), ("register_name", 1)]))
    receipts = list(
        database["transactions"].find(
            {"sales_channel": "Point of Sale"},
            sort=[("timestamp", -1)],
            limit=100,
        )
    )
    payment_mix = {}
    for terminal in terminals:
        for method, count in (terminal.get("payment_mix") or {}).items():
            payment_mix[method] = payment_mix.get(method, 0) + int(count or 0)
    return render_template(
        "point_of_sale.html",
        page="point_of_sale",
        terminals=terminals,
        receipts=receipts,
        payment_mix=sorted(payment_mix.items()),
        metrics=get_business_metrics(database),
    )


@views_bp.route("/cashpoints")
@login_required
def cashpoints():
    database = db()
    ledger = list(database["cashpoints_ledger"].find({}, sort=[("timestamp", -1)], limit=80))
    top_balances = list(database["buyers"].find({}, sort=[("cashpoints_balance", -1)], limit=10))
    return render_template(
        "cashpoints.html",
        page="cashpoints",
        ledger=ledger,
        top_balances=top_balances,
    )


@views_bp.route("/transactions")
@login_required
def transactions():
    transaction_list = list(db()["transactions"].find({}, sort=[("timestamp", -1)], limit=120))
    return render_template("transactions.html", page="transactions", transactions=transaction_list)


@views_bp.route("/agent-activity")
@login_required
def agent_activity():
    logs = list(db()["agent_activity_log"].find({}, sort=[("timestamp", -1)], limit=160))
    return render_template("agent_activity.html", page="agent_activity", logs=logs)
