from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .utils import serialize_document, utcnow


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def calculate_business_metrics(db) -> dict:
    now = utcnow()
    today = now.date()
    transactions = list(db["transactions"].find({}))
    buyers = list(db["buyers"].find({}))
    products = list(db["products"].find({}))
    ledger = list(db["cashpoints_ledger"].find({}))
    terminals = list(db["pos_terminals"].find({}))
    pos_transactions = [txn for txn in transactions if txn.get("sales_channel") == "Point of Sale"]

    completed_revenue = sum(
        float(txn.get("amount", 0))
        for txn in transactions
        if txn.get("status") in {"Completed", "Pending"}
    )
    orders_today = sum(
        1
        for txn in transactions
        if _as_utc(txn.get("timestamp")) and _as_utc(txn.get("timestamp")).date() == today
    )
    active_cutoff = now - timedelta(days=3)
    active_buyers = sum(
        1
        for buyer in buyers
        if buyer.get("status") == "Active"
        and _as_utc(buyer.get("last_active"))
        and _as_utc(buyer.get("last_active")) >= active_cutoff
    )
    low_stock_products = sum(
        1
        for product in products
        if int(product.get("stock", 0)) <= int(product.get("low_stock_threshold", 0))
    )
    total_cashpoints_issued = sum(
        int(entry.get("points", 0))
        for entry in ledger
        if int(entry.get("points", 0)) > 0
    )
    suspicious_transactions = sum(
        1 for txn in transactions if txn.get("suspicious") or txn.get("status") == "Flagged"
    )
    product_views = sum(int(product.get("views_count", 0)) for product in products)
    purchases = sum(1 for txn in transactions if txn.get("status") in {"Completed", "Pending"})
    conversion_rate = round((purchases / product_views) * 100, 1) if product_views else 0.0
    decision_test_cases_covered = sorted(
        {txn.get("decision_test_case") for txn in transactions if txn.get("decision_test_case")}
    )
    policy_blocks = sum(
        1
        for txn in transactions
        for check in txn.get("policy_checks", [])
        if check.get("outcome") == "blocked"
    )
    approval_queue = sum(1 for txn in transactions if txn.get("approval_required"))
    connector_retries = sum(
        1
        for txn in transactions
        if (txn.get("execution_receipt") or {}).get("status") == "Retrying"
    )
    pos_revenue = sum(
        float(txn.get("amount", 0))
        for txn in pos_transactions
        if txn.get("status") in {"Completed", "Pending"}
    )
    pos_orders_today = sum(
        1
        for txn in pos_transactions
        if _as_utc(txn.get("timestamp")) and _as_utc(txn.get("timestamp")).date() == today
    )
    pos_active_terminals = sum(1 for terminal in terminals if terminal.get("status") != "Offline")
    pos_queue_depth = sum(int(terminal.get("queue_depth", 0)) for terminal in terminals)

    return {
        "_id": "current",
        "total_revenue": round(completed_revenue, 2),
        "orders_today": orders_today,
        "active_buyers": active_buyers,
        "low_stock_products": low_stock_products,
        "total_cashpoints_issued": total_cashpoints_issued,
        "suspicious_transactions": suspicious_transactions,
        "conversion_rate": conversion_rate,
        "decision_test_cases_covered": decision_test_cases_covered,
        "decision_test_case_count": len(decision_test_cases_covered),
        "policy_blocks": policy_blocks,
        "approval_queue": approval_queue,
        "connector_retries": connector_retries,
        "decision_audit_records": sum(1 for txn in transactions if txn.get("decision_context_pack")),
        "pos_revenue": round(pos_revenue, 2),
        "pos_orders_today": pos_orders_today,
        "pos_active_terminals": pos_active_terminals,
        "pos_queue_depth": pos_queue_depth,
        "updated_at": now,
    }


def recalculate_and_store_metrics(db) -> dict:
    metrics = calculate_business_metrics(db)
    db["business_metrics"].replace_one({"_id": "current"}, metrics, upsert=True)
    return metrics


def get_business_metrics(db) -> dict:
    metrics = db["business_metrics"].find_one({"_id": "current"})
    if not metrics:
        metrics = recalculate_and_store_metrics(db)
    return serialize_document(metrics)
