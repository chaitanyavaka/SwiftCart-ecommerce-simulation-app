from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any


DECISION_POLICY_VERSION = "tenant_swiftcart_policy_2026_06_01"
DECISION_MODEL_VERSION = "swiftcart-commerce-runtime-0.3"
DECISION_CONTEXT_PACK_VERSION = "decision_context_pack.v1"
DECISION_ACTION_GRAPH_VERSION = "action_graph.v1"

DECISION_POLICY_IDS = {
    "reward_cap": "policy.loyalty.reward_cap.v4",
    "margin_floor": "policy.commerce.margin_floor.v12",
    "fraud_velocity": "policy.fraud.redemption_velocity.v7",
    "consent": "policy.privacy.personalization_consent.v6",
    "inventory": "policy.inventory.availability.v5",
    "partner_liability": "policy.partner.liability_split.v3",
    "approval": "policy.approval.high_value_action.v2",
    "experiment": "policy.experiment.holdout_integrity.v2",
}

DECISION_TEST_CASES = [
    {
        "key": "loyalty_reward_allowed",
        "title": "Loyalty reward allowed",
        "domain": "loyalty.checkout_reward",
        "decision_class": "allow",
        "action_type": "issue_cashpoints",
        "autonomy_level": "Level 3 - Bounded Autonomy",
        "approval_required": False,
        "approval_status": "Not Required",
        "action_graph_status": "Completed",
        "execution_status": "Completed",
        "connector_id": "loyalty_core_v3",
        "connector_family": "loyalty_core",
        "rollback_available": True,
        "holdout_group": False,
        "expected_result": "Reward is issued inside customer cap and margin rules.",
    },
    {
        "key": "fraud_redemption_review",
        "title": "Fraud redemption review",
        "domain": "fraud.redemption_governance",
        "decision_class": "review",
        "action_type": "create_fraud_case",
        "autonomy_level": "Level 2 - Assist",
        "approval_required": True,
        "approval_status": "Awaiting Review",
        "action_graph_status": "AwaitingApproval",
        "execution_status": "Paused",
        "connector_id": "fraud_system_v2",
        "connector_family": "fraud_system",
        "rollback_available": False,
        "holdout_group": False,
        "expected_result": "High-risk redemption is paused for analyst review.",
    },
    {
        "key": "margin_floor_block",
        "title": "Margin floor block",
        "domain": "promotion.margin_guard",
        "decision_class": "block",
        "action_type": "reject_discount",
        "autonomy_level": "Level 1 - Draft",
        "approval_required": False,
        "approval_status": "Rejected By Policy",
        "action_graph_status": "Rejected",
        "execution_status": "Not Executed",
        "connector_id": "pricing_engine_v2",
        "connector_family": "pricing_engine",
        "rollback_available": False,
        "holdout_group": False,
        "expected_result": "Discount is blocked before it can breach margin floor.",
    },
    {
        "key": "consent_personalization_block",
        "title": "Consent personalization block",
        "domain": "journey.personalization",
        "decision_class": "block",
        "action_type": "suppress_personalized_offer",
        "autonomy_level": "Level 0 - Observe",
        "approval_required": False,
        "approval_status": "Rejected By Policy",
        "action_graph_status": "Rejected",
        "execution_status": "Not Executed",
        "connector_id": "marketing_cloud_v4",
        "connector_family": "marketing_automation",
        "rollback_available": False,
        "holdout_group": False,
        "expected_result": "Personalized action is suppressed when consent is missing.",
    },
    {
        "key": "inventory_low_stock_block",
        "title": "Inventory low-stock block",
        "domain": "inventory.offer_eligibility",
        "decision_class": "block",
        "action_type": "withhold_offer",
        "autonomy_level": "Level 1 - Draft",
        "approval_required": False,
        "approval_status": "Rejected By Policy",
        "action_graph_status": "Rejected",
        "execution_status": "Not Executed",
        "connector_id": "inventory_system_v3",
        "connector_family": "inventory_system",
        "rollback_available": False,
        "holdout_group": False,
        "expected_result": "Offer is withheld when available stock is below the policy threshold.",
    },
    {
        "key": "approval_required_high_value",
        "title": "High-value approval required",
        "domain": "promotion.approval_gate",
        "decision_class": "review",
        "action_type": "queue_high_value_offer",
        "autonomy_level": "Level 2 - Assist",
        "approval_required": True,
        "approval_status": "Awaiting Approval",
        "action_graph_status": "AwaitingApproval",
        "execution_status": "Paused",
        "connector_id": "crm_campaigns_v2",
        "connector_family": "crm",
        "rollback_available": True,
        "holdout_group": False,
        "expected_result": "High-value action waits for human approval.",
    },
    {
        "key": "connector_retry",
        "title": "Connector retry path",
        "domain": "execution.connector_resilience",
        "decision_class": "allow",
        "action_type": "retry_connector_action",
        "autonomy_level": "Level 3 - Bounded Autonomy",
        "approval_required": False,
        "approval_status": "Not Required",
        "action_graph_status": "Retrying",
        "execution_status": "Retrying",
        "connector_id": "ecommerce_platform_v3",
        "connector_family": "ecommerce_platform",
        "rollback_available": True,
        "holdout_group": False,
        "expected_result": "Transient connector failure is retried with an execution receipt.",
    },
    {
        "key": "holdout_experiment",
        "title": "Experiment holdout",
        "domain": "promotion.experimentation",
        "decision_class": "dry_run",
        "action_type": "assign_holdout",
        "autonomy_level": "Level 0 - Observe",
        "approval_required": False,
        "approval_status": "Not Required",
        "action_graph_status": "Completed",
        "execution_status": "Completed",
        "connector_id": "experimentation_service_v1",
        "connector_family": "experimentation",
        "rollback_available": False,
        "holdout_group": True,
        "expected_result": "Customer is held out to preserve incrementality measurement.",
    },
    {
        "key": "rollback_available",
        "title": "Rollback-ready execution",
        "domain": "execution.rollback",
        "decision_class": "allow",
        "action_type": "apply_reversible_offer",
        "autonomy_level": "Level 3 - Bounded Autonomy",
        "approval_required": False,
        "approval_status": "Not Required",
        "action_graph_status": "Completed",
        "execution_status": "Completed",
        "connector_id": "loyalty_core_v3",
        "connector_family": "loyalty_core",
        "rollback_available": True,
        "holdout_group": False,
        "expected_result": "Action includes a compensation path and rollback receipt.",
    },
    {
        "key": "deterministic_fallback",
        "title": "Deterministic fallback",
        "domain": "decision.degraded_mode",
        "decision_class": "allow",
        "action_type": "rules_fallback_reward",
        "autonomy_level": "Level 3 - Bounded Autonomy",
        "approval_required": False,
        "approval_status": "Not Required",
        "action_graph_status": "Completed",
        "execution_status": "Completed",
        "connector_id": "rules_engine_v1",
        "connector_family": "rules_engine",
        "rollback_available": True,
        "holdout_group": False,
        "expected_result": "Decision is produced by deterministic rules during model fallback.",
    },
]

DECISION_TEST_CASE_KEYS = [case["key"] for case in DECISION_TEST_CASES]


def scenario_for_index(index: int) -> dict[str, Any]:
    return DECISION_TEST_CASES[(max(1, int(index)) - 1) % len(DECISION_TEST_CASES)]


def scenario_for_key(key: str) -> dict[str, Any]:
    for scenario in DECISION_TEST_CASES:
        if scenario["key"] == key:
            return scenario
    return DECISION_TEST_CASES[0]


def stable_hash(*parts: Any, length: int = 12) -> str:
    text = "|".join(str(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def build_decision_metadata(
    *,
    source: str,
    sequence: int | str,
    buyer: dict[str, Any],
    product: dict[str, Any],
    amount: float,
    quantity: int,
    timestamp: datetime,
    scenario_key: str | None = None,
    suspicious: bool = False,
    status: str | None = None,
) -> dict[str, Any]:
    scenario = scenario_for_key(scenario_key) if scenario_key else scenario_for_index(int(sequence) if str(sequence).isdigit() else 1)
    buyer_id = buyer.get("buyer_id") or buyer.get("_id") or "buyer"
    product_id = product.get("product_id") or product.get("_id") or "product"
    digest = stable_hash(source, sequence, buyer_id, product_id, amount, quantity, scenario["key"])
    decision_id = f"dec-{digest}"
    request_id = f"req-{stable_hash(decision_id, timestamp.isoformat(), length=10)}"
    context_hash = stable_hash(buyer_id, product_id, amount, scenario["key"], DECISION_POLICY_VERSION, length=16)
    approval_required = bool(scenario["approval_required"] or suspicious)
    policy_checks = _build_policy_checks(scenario, buyer, product, amount, suspicious)
    evidence_refs = _build_evidence_refs(buyer, product)
    action_graph = _build_action_graph(scenario, decision_id, policy_checks)
    execution_receipt = _build_execution_receipt(scenario, decision_id, timestamp)
    return {
        "event_type": "checkout.purchase",
        "channel": _channel_for_sequence(sequence),
        "decision_id": decision_id,
        "request_id": request_id,
        "idempotency_key": f"tenant_swiftcart:{request_id}:{scenario['action_type']}",
        "context_hash": context_hash,
        "policy_version": DECISION_POLICY_VERSION,
        "model_version": DECISION_MODEL_VERSION,
        "decision_class": scenario["decision_class"],
        "decision_domain": scenario["domain"],
        "decision_test_case": scenario["key"],
        "decision_test_title": scenario["title"],
        "decision_expected_result": scenario["expected_result"],
        "policy_checks": policy_checks,
        "approval_required": approval_required,
        "approval_status": "Awaiting Review" if suspicious else scenario["approval_status"],
        "approval_chain": _build_approval_chain(scenario, approval_required, suspicious),
        "autonomy_level": scenario["autonomy_level"],
        "action_graph_status": scenario["action_graph_status"],
        "action_graph": action_graph,
        "execution_receipt": execution_receipt,
        "rollback_available": scenario["rollback_available"],
        "latency_ms": _latency_for_scenario(scenario),
        "expected_margin_impact": _margin_impact(product, amount, scenario),
        "fraud_signals": _fraud_signals(buyer, suspicious, scenario),
        "consent_status": buyer.get("consent_status", "granted"),
        "experiment_key": "sc-repeat-value-2026-06",
        "holdout_group": scenario["holdout_group"],
        "evidence_refs": evidence_refs,
        "decision_context_pack": _build_context_pack(
            scenario=scenario,
            buyer=buyer,
            product=product,
            context_hash=context_hash,
            evidence_refs=evidence_refs,
        ),
        "final_decision": _final_decision(status, scenario, suspicious),
    }


def build_ledger_metadata(
    *,
    source: str,
    sequence: int | str,
    buyer: dict[str, Any],
    points: int,
    timestamp: datetime,
    scenario_key: str = "loyalty_reward_allowed",
    suspicious: bool = False,
) -> dict[str, Any]:
    scenario = scenario_for_key("fraud_redemption_review" if suspicious else scenario_key)
    buyer_id = buyer.get("buyer_id") or buyer.get("_id") or "buyer"
    digest = stable_hash(source, sequence, buyer_id, points, scenario["key"])
    decision_id = f"dec-wallet-{digest}"
    request_id = f"req-wallet-{stable_hash(decision_id, timestamp.isoformat(), length=10)}"
    return {
        "decision_id": decision_id,
        "request_id": request_id,
        "idempotency_key": f"tenant_swiftcart:{request_id}:cashpoints_ledger",
        "context_hash": stable_hash(buyer_id, points, scenario["key"], DECISION_POLICY_VERSION, length=16),
        "policy_version": DECISION_POLICY_VERSION,
        "model_version": DECISION_MODEL_VERSION,
        "decision_domain": "loyalty.wallet_governance",
        "decision_class": "review" if suspicious else "allow",
        "decision_test_case": scenario["key"],
        "approval_required": suspicious,
        "approval_status": "Awaiting Review" if suspicious else "Not Required",
        "autonomy_level": "Level 2 - Assist" if suspicious else "Level 3 - Bounded Autonomy",
        "wallet_policy_result": "review" if suspicious else "passed",
        "liability_owner": "SwiftCart" if points >= 0 else "Seller Partner",
        "redemption_velocity": "high" if suspicious else "normal",
        "execution_receipt": _build_execution_receipt(scenario, decision_id, timestamp),
    }


def _build_policy_checks(
    scenario: dict[str, Any],
    buyer: dict[str, Any],
    product: dict[str, Any],
    amount: float,
    suspicious: bool,
) -> list[dict[str, Any]]:
    consent_blocked = scenario["key"] == "consent_personalization_block" or buyer.get("consent_status") == "opted_out"
    margin_blocked = scenario["key"] == "margin_floor_block"
    inventory_blocked = scenario["key"] == "inventory_low_stock_block" or int(product.get("stock", 0)) <= int(
        product.get("low_stock_threshold", 0)
    )
    fraud_review = suspicious or scenario["key"] == "fraud_redemption_review"
    approval_review = scenario["approval_required"] or fraud_review
    partner_blocked = float(product.get("partner_liability_pct", 0)) > 0.65
    return [
        _policy_check(
            DECISION_POLICY_IDS["reward_cap"],
            "passed" if int(buyer.get("reward_cap_remaining", 0)) >= max(1, int(amount * 0.05)) else "blocked",
            "Customer reward cap covers the proposed value.",
            "Loyalty Ops",
        ),
        _policy_check(
            DECISION_POLICY_IDS["margin_floor"],
            "blocked" if margin_blocked else "passed",
            "Gross margin is compared with product-level floor.",
            "Finance",
        ),
        _policy_check(
            DECISION_POLICY_IDS["fraud_velocity"],
            "review" if fraud_review else "passed",
            "Velocity and risk signals are inside marketplace norms.",
            "Risk",
        ),
        _policy_check(
            DECISION_POLICY_IDS["consent"],
            "blocked" if consent_blocked else "passed",
            "Personalization is allowed only with customer consent.",
            "Compliance",
        ),
        _policy_check(
            DECISION_POLICY_IDS["inventory"],
            "blocked" if inventory_blocked else "passed",
            "Offer eligibility requires enough sellable stock.",
            "Inventory Ops",
        ),
        _policy_check(
            DECISION_POLICY_IDS["partner_liability"],
            "review" if partner_blocked else "passed",
            "Partner liability share stays inside contract tolerance.",
            "Partner Ops",
        ),
        _policy_check(
            DECISION_POLICY_IDS["approval"],
            "review" if approval_review else "not_required",
            "High-value or high-risk actions require human approval.",
            "Commercial Governance",
        ),
        _policy_check(
            DECISION_POLICY_IDS["experiment"],
            "holdout" if scenario["holdout_group"] else "passed",
            "Experiment assignment is preserved for incrementality testing.",
            "Growth Analytics",
        ),
    ]


def _policy_check(policy_id: str, outcome: str, detail: str, owner: str) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "version": DECISION_POLICY_VERSION,
        "outcome": outcome,
        "detail": detail,
        "owner": owner,
    }


def _build_evidence_refs(buyer: dict[str, Any], product: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "customer_profile",
            "ref": buyer.get("buyer_id") or buyer.get("_id"),
            "fields": ["segment", "cashpoints_balance", "risk_score", "consent_status"],
            "freshness": "hot",
        },
        {
            "type": "product_catalog",
            "ref": product.get("product_id") or product.get("_id"),
            "fields": ["price", "stock", "gross_margin_pct", "discount_pct"],
            "freshness": "hot",
        },
        {
            "type": "policy_bundle",
            "ref": DECISION_POLICY_VERSION,
            "fields": ["reward_cap", "margin_floor", "fraud_velocity", "approval"],
            "freshness": "pinned",
        },
    ]


def _build_context_pack(
    *,
    scenario: dict[str, Any],
    buyer: dict[str, Any],
    product: dict[str, Any],
    context_hash: str,
    evidence_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    policy_blocked = []
    if scenario["key"] == "consent_personalization_block":
        policy_blocked.append({"field": "personalized_channel_offer", "reason": "missing_or_limited_consent"})
    if scenario["key"] == "margin_floor_block":
        policy_blocked.append({"field": "extra_discount_pct", "reason": "margin_floor_violation"})
    if scenario["key"] == "inventory_low_stock_block":
        policy_blocked.append({"field": "promotion_eligibility", "reason": "low_stock"})
    missing_context = []
    if scenario["key"] == "connector_retry":
        missing_context.append({"field": "downstream_receipt", "reason": "connector_retry_in_progress"})
    return {
        "pack_id": f"dcp-{context_hash[:12]}",
        "version": DECISION_CONTEXT_PACK_VERSION,
        "context_hash": context_hash,
        "available_context": [
            "customer_profile",
            "loyalty_wallet",
            "product_catalog",
            "seller_connector",
            "policy_bundle",
            "recent_transactions",
        ],
        "admitted_context": [
            "segment",
            "cashpoints_balance",
            "risk_score",
            "consent_status",
            "price",
            "stock",
            "gross_margin_pct",
        ],
        "rejected_context": [
            {"field": "raw_payment_token", "reason": "not_required_for_decision"},
            {"field": "sensitive_demographics", "reason": "not_permitted"},
        ],
        "missing_context": missing_context,
        "policy_blocked_context": policy_blocked,
        "identity_resolution": {
            "customer_id": buyer.get("buyer_id") or buyer.get("_id"),
            "household_id": buyer.get("household_id"),
            "device_fingerprint": buyer.get("device_fingerprint"),
        },
        "commercial_context": {
            "product_id": product.get("product_id") or product.get("_id"),
            "campaign_id": product.get("campaign_id"),
            "inventory_policy_status": product.get("inventory_policy_status"),
        },
        "evidence_refs": evidence_refs,
    }


def _build_action_graph(scenario: dict[str, Any], decision_id: str, policy_checks: list[dict[str, Any]]) -> dict[str, Any]:
    policy_status = "Completed"
    if any(check["outcome"] == "blocked" for check in policy_checks):
        policy_status = "Rejected"
    elif any(check["outcome"] == "review" for check in policy_checks):
        policy_status = "Review"
    execute_status = scenario["execution_status"]
    return {
        "graph_id": f"ag-{decision_id.replace('dec-', '')}",
        "schema_version": DECISION_ACTION_GRAPH_VERSION,
        "status": scenario["action_graph_status"],
        "nodes": [
            {
                "node_id": "policy_preflight",
                "type": "policy_check",
                "status": policy_status,
                "policy_refs": [check["policy_id"] for check in policy_checks],
            },
            {
                "node_id": "compile_action",
                "type": "action_compiler",
                "status": "Completed" if scenario["action_graph_status"] != "Rejected" else "Rejected",
                "action_type": scenario["action_type"],
            },
            {
                "node_id": "execute_action",
                "type": "connector_action",
                "status": execute_status,
                "connector_id": scenario["connector_id"],
                "idempotency_required": True,
            },
        ],
        "edges": [
            {"from": "policy_preflight", "to": "compile_action"},
            {"from": "compile_action", "to": "execute_action"},
        ],
        "rollback": {
            "available": scenario["rollback_available"],
            "strategy": "compensating_transaction" if scenario["rollback_available"] else "not_applicable",
        },
    }


def _build_execution_receipt(scenario: dict[str, Any], decision_id: str, timestamp: datetime) -> dict[str, Any]:
    attempts = 2 if scenario["key"] == "connector_retry" else 1
    status = scenario["execution_status"]
    return {
        "receipt_id": f"erc-{decision_id.replace('dec-', '')}",
        "connector_id": scenario["connector_id"],
        "connector_family": scenario["connector_family"],
        "operation": scenario["action_type"],
        "status": status,
        "attempts": attempts,
        "latency_ms": _latency_for_scenario(scenario),
        "completed_at": timestamp if status in {"Completed", "Paused", "Not Executed"} else None,
        "error_code": "CONNECTOR_TIMEOUT_RETRYING" if scenario["key"] == "connector_retry" else None,
        "dead_lettered": False,
    }


def _build_approval_chain(scenario: dict[str, Any], approval_required: bool, suspicious: bool) -> list[dict[str, Any]]:
    if not approval_required:
        return []
    queue = "Fraud Review" if suspicious or scenario["key"] == "fraud_redemption_review" else "Commercial Approval"
    return [
        {
            "step": "human_review",
            "queue": queue,
            "status": "pending",
            "required_policy": DECISION_POLICY_IDS["approval"],
        }
    ]


def _latency_for_scenario(scenario: dict[str, Any]) -> int:
    if scenario["key"] == "connector_retry":
        return 1850
    if scenario["approval_required"]:
        return 420
    if scenario["decision_class"] == "block":
        return 74
    if scenario["key"] == "deterministic_fallback":
        return 38
    return 118


def _margin_impact(product: dict[str, Any], amount: float, scenario: dict[str, Any]) -> dict[str, Any]:
    margin_pct = float(product.get("gross_margin_pct", 0.32))
    margin_floor = float(product.get("margin_floor_pct", 0.18))
    projected_margin = round(amount * margin_pct, 2)
    return {
        "gross_margin_pct": round(margin_pct, 3),
        "margin_floor_pct": round(margin_floor, 3),
        "projected_margin": projected_margin,
        "margin_floor_breached": scenario["key"] == "margin_floor_block" or margin_pct < margin_floor,
    }


def _fraud_signals(buyer: dict[str, Any], suspicious: bool, scenario: dict[str, Any]) -> dict[str, Any]:
    high_risk = suspicious or scenario["key"] == "fraud_redemption_review"
    return {
        "risk_score": round(float(buyer.get("risk_score", 0.1)), 2),
        "redemption_velocity": "high" if high_risk else "normal",
        "device_reuse_count": 7 if high_risk else 1,
        "geo_velocity": "unusual" if high_risk else "normal",
        "case_required": high_risk,
    }


def _final_decision(status: str | None, scenario: dict[str, Any], suspicious: bool) -> dict[str, Any]:
    if suspicious or scenario["decision_class"] == "review":
        outcome = "review"
    elif scenario["decision_class"] == "block":
        outcome = "block"
    else:
        outcome = "allow"
    return {
        "outcome": outcome,
        "commerce_status": status,
        "reason_code": scenario["key"],
    }


def _channel_for_sequence(sequence: int | str) -> str:
    channels = ["web", "mobile_app", "partner_marketplace", "store_pos"]
    try:
        index = int(sequence)
    except (TypeError, ValueError):
        index = int(stable_hash(sequence, length=2), 16)
    return channels[index % len(channels)]
