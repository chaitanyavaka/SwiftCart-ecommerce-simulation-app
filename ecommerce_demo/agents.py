from __future__ import annotations

import random
import threading
import time
import uuid
from datetime import timedelta
from typing import Any

from .metrics import recalculate_and_store_metrics
from .decision_fixtures import (
    DECISION_POLICY_VERSION,
    build_decision_metadata,
    build_ledger_metadata,
)
from .reasons import ReasonGenerator
from .seed import seed_demo_data
from .utils import clamp, serialize_value, slugify, utcnow


SPEED_RANGES = {
    "five_minute": (300, 300),
    "fast": (300, 300),
    "demo": (300, 300),
    "realistic": (300, 300),
}

BUYER_EVENTS_PER_CYCLE = (14, 22)
BUYER_EVENT_WEIGHTS = [28, 24, 36, 12]
INVENTORY_PROCESS_LIMIT = 24
LOW_STOCK_SCAN_LIMIT = 24
SELLER_UPDATES_PER_CYCLE = 5
REWARD_PROCESS_LIMIT = 24
PROMOTION_UPDATES_PER_CYCLE = (5, 9)
FRAUD_TRANSACTIONS_PER_CYCLE = (1, 3)
SUSPICIOUS_REDEMPTIONS_PER_CYCLE = (1, 2)
CATALOG_LAUNCHES_PER_CYCLE = (1, 2)
CATALOG_LAUNCH_PROBABILITY = 0.9
POS_SALES_PER_CYCLE = (6, 10)
POS_PAYMENT_METHODS = ["UPI", "Card", "Cash", "Wallet"]
POS_DECISION_SCENARIOS = [
    "loyalty_reward_allowed",
    "loyalty_reward_allowed",
    "connector_retry",
    "rollback_available",
    "deterministic_fallback",
]

CATALOG_LAUNCH_TERMS = {
    "Beauty": ["Glow", "Hydra", "Silk", "Bloom", "Dew"],
    "Electronics": ["Nova", "Volt", "Pulse", "Aero", "Snap"],
    "Grocery": ["Farm", "Pantry", "Harvest", "Golden", "Fresh"],
    "Home": ["Nest", "Cloud", "Pure", "Stack", "Bright"],
    "Kids": ["Junior", "Robo", "Tiny", "Story", "Doodle"],
    "Lifestyle": ["Urban", "Studio", "Zen", "Focus", "Mood"],
    "Outdoor": ["Trail", "Summit", "Terra", "Base", "Camp"],
}

CATALOG_LAUNCH_PRODUCTS = {
    "Beauty": ["Serum Set", "Body Mist", "Lip Balm Trio", "Hair Ritual Kit"],
    "Electronics": ["Bluetooth Tracker", "Smart Plug", "Charging Dock", "Creator Light"],
    "Grocery": ["Snack Box", "Breakfast Mix", "Tea Tin", "Protein Pack"],
    "Home": ["Storage Basket", "Desk Lamp", "Kitchen Set", "Bath Organizer"],
    "Kids": ["Puzzle Kit", "Craft Box", "Learning Cards", "Activity Mat"],
    "Lifestyle": ["Desk Kit", "Travel Pouch", "Yoga Strap", "Reading Light"],
    "Outdoor": ["Travel Flask", "Trail Pouch", "Rain Cover", "Camp Mat"],
}


class SimulationEngine:
    def __init__(
        self,
        db,
        groq_api_key: str | None = None,
        groq_model: str | None = None,
        random_seed: str | int | None = None,
        interval_seconds: int = 300,
    ):
        self.db = db
        self.reasons = ReasonGenerator(groq_api_key, groq_model)
        self.random = random.Random(random_seed)
        self.interval_seconds = max(60, int(interval_seconds))
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> dict:
        with self._lock:
            self._set_config({"running": True, "updated_at": utcnow()})
            self._log_action(
                "Simulation Control Agent",
                "simulation",
                "simulation_config",
                "main",
                {"running": False},
                {"running": True},
                {"state": "started"},
            )
            if not self._thread or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._loop, name="swiftcart-agents", daemon=True)
                self._thread.start()
            return self.get_config()

    def stop(self) -> dict:
        with self._lock:
            self._set_config({"running": False, "updated_at": utcnow()})
            self._stop_event.set()
            self._log_action(
                "Simulation Control Agent",
                "simulation",
                "simulation_config",
                "main",
                {"running": True},
                {"running": False},
                {"state": "stopped"},
            )
        self._join_scheduler_thread()
        return self.get_config()

    def set_speed(self, speed: str) -> dict:
        if speed not in SPEED_RANGES:
            raise ValueError(f"Unsupported speed: {speed}")
        interval_seconds = self._next_interval(speed)
        previous = self.get_config()
        self._set_config({"speed": speed, "interval_seconds": interval_seconds, "updated_at": utcnow()})
        self._log_action(
            "Simulation Control Agent",
            "simulation",
            "simulation_config",
            "main",
            {"speed": previous.get("speed"), "interval_seconds": previous.get("interval_seconds")},
            {"speed": speed, "interval_seconds": interval_seconds},
            {"state": "speed_changed"},
        )
        return self.get_config()

    def reset_demo_data(self, max_discount_pct: int | None = None) -> dict:
        self._stop_event.set()
        self._join_scheduler_thread()
        with self._lock:
            current_config = self.get_config()
            seed_demo_data(
                self.db,
                max_discount_pct=max_discount_pct or int(current_config.get("max_discount_pct", 25)),
            )
            self._set_config({"running": False, "speed": current_config.get("speed", "five_minute"), "updated_at": utcnow()})
            self._log_action(
                "Simulation Control Agent",
                "simulation",
                "simulation_config",
                "main",
                {"reset": False},
                {"reset": True},
                {"state": "reset"},
            )
            return self.get_config()

    def _join_scheduler_thread(self) -> None:
        if self._thread and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        if self._thread and not self._thread.is_alive():
            self._thread = None

    def get_config(self) -> dict:
        config = self.db["simulation_config"].find_one({"_id": "main"})
        if not config:
            config = {
                "_id": "main",
                "running": False,
                "speed": "five_minute",
                "interval_seconds": self.interval_seconds,
                "max_discount_pct": 25,
                "tick_count": 0,
                "updated_at": utcnow(),
            }
            self.db["simulation_config"].insert_one(config)
        return config

    def run_cycle(self) -> None:
        with self._lock:
            self._buyer_activity_agent()
            self._point_of_sale_agent()
            self._inventory_agent()
            self._seller_agent()
            self._cashpoints_agent()
            self._pricing_promotion_agent()
            self._fraud_anomaly_agent()
            self._metrics_agent()
            config = self.get_config()
            self._set_config(
                {
                    "tick_count": int(config.get("tick_count", 0)) + 1,
                    "updated_at": utcnow(),
                }
            )

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            config = self.get_config()
            if config.get("running"):
                self.run_cycle()
                speed = self.get_config().get("speed", "five_minute")
                self._set_config({"interval_seconds": self._next_interval(speed), "updated_at": utcnow()})
            wait_seconds = int(self.get_config().get("interval_seconds", 45))
            self._stop_event.wait(wait_seconds)

    def _buyer_activity_agent(self) -> None:
        agent = "Buyer Activity Agent"
        products = list(self.db["products"].find({"seller_status": "Active"}))
        buyers = list(self.db["buyers"].find({}))
        if not products or not buyers:
            return

        event_count = self.random.randint(*BUYER_EVENTS_PER_CYCLE)
        for _ in range(event_count):
            buyer = self.random.choice(buyers)
            product = self.random.choice(products)
            event_type = self.random.choices(
                ["view", "cart", "purchase", "abandoned_cart"],
                weights=BUYER_EVENT_WEIGHTS,
            )[0]
            now = utcnow()

            if event_type == "view":
                old = {"views_count": product.get("views_count", 0)}
                self.db["products"].update_one(
                    {"_id": product["_id"]},
                    {"$inc": {"views_count": 1}, "$set": {"updated_at": now}},
                )
                self.db["buyers"].update_one({"_id": buyer["_id"]}, {"$set": {"last_active": now, "status": "Active"}})
                self._log_action(
                    agent,
                    "view",
                    "products",
                    product["_id"],
                    old,
                    {"views_count": old["views_count"] + 1},
                    {"product": product["name"], "buyer": buyer["segment"]},
                )

            elif event_type == "cart":
                old = {"carts_count": product.get("carts_count", 0)}
                self.db["products"].update_one(
                    {"_id": product["_id"]},
                    {"$inc": {"carts_count": 1}, "$set": {"updated_at": now}},
                )
                self.db["buyers"].update_one({"_id": buyer["_id"]}, {"$set": {"last_active": now, "status": "Active"}})
                self._log_action(
                    agent,
                    "cart",
                    "products",
                    product["_id"],
                    old,
                    {"carts_count": old["carts_count"] + 1},
                    {"product": product["name"], "buyer": buyer["segment"]},
                )

            elif event_type == "purchase":
                fresh_product = self.db["products"].find_one({"_id": product["_id"]})
                if not fresh_product or int(fresh_product.get("stock", 0)) <= 0:
                    self._log_action(
                        agent,
                        "purchase",
                        "products",
                        product["_id"],
                        {"stock": product.get("stock", 0)},
                        {"purchase_created": False},
                        {"blocked": "out_of_stock"},
                        validation_status="skipped",
                    )
                    continue
                quantity = min(self.random.randint(1, 4), int(fresh_product["stock"]))
                amount = round(float(fresh_product["price"]) * quantity, 2)
                transaction_id = f"txn-{uuid.uuid4().hex[:10]}"
                scenario_key = self._choose_purchase_scenario(buyer, fresh_product, amount)
                if scenario_key in {"margin_floor_block", "consent_personalization_block", "inventory_low_stock_block"}:
                    status = "Cancelled"
                elif scenario_key in {"approval_required_high_value", "connector_retry"}:
                    status = "Pending"
                else:
                    status = self.random.choices(["Completed", "Pending"], weights=[82, 18])[0]
                decision_metadata = build_decision_metadata(
                    source="agent-purchase",
                    sequence=transaction_id,
                    buyer=buyer,
                    product=fresh_product,
                    amount=amount,
                    quantity=quantity,
                    timestamp=now,
                    scenario_key=scenario_key,
                    suspicious=False,
                    status=status,
                )
                transaction = {
                    "_id": transaction_id,
                    "transaction_id": transaction_id,
                    "buyer_id": buyer["buyer_id"],
                    "buyer_name": buyer["name"],
                    "seller_id": fresh_product["seller_id"],
                    "product_id": fresh_product["product_id"],
                    "product_name": fresh_product["name"],
                    "quantity": quantity,
                    "amount": amount,
                    "status": status,
                    "suspicious": False,
                    "risk_score": buyer.get("risk_score", 0.1),
                    "inventory_applied": status not in {"Completed", "Pending"},
                    "inventory_quantity_applied": 0,
                    "points_applied": False,
                    "timestamp": now,
                    **decision_metadata,
                }
                self.db["transactions"].insert_one(transaction)
                buyer_inc = {"orders_count": 1, "lifetime_value": amount} if status in {"Completed", "Pending"} else {}
                buyer_update = {"$set": {"last_active": now, "status": "Active"}}
                if buyer_inc:
                    buyer_update["$inc"] = buyer_inc
                self.db["buyers"].update_one({"_id": buyer["_id"]}, buyer_update)
                seller_inc = {}
                if status in {"Completed", "Pending"}:
                    seller_inc["revenue"] = amount
                if status == "Pending":
                    seller_inc["pending_orders"] = 1
                seller_update = {"$set": {"updated_at": now}}
                if seller_inc:
                    seller_update["$inc"] = seller_inc
                self.db["sellers"].update_one({"_id": fresh_product["seller_id"]}, seller_update)
                self._log_action(
                    agent,
                    "purchase",
                    "transactions",
                    transaction_id,
                    {},
                    {"amount": amount, "quantity": quantity, "status": status},
                    {
                        "product": fresh_product["name"],
                        "buyer": buyer["segment"],
                        "decision_id": decision_metadata["decision_id"],
                        "decision_test_case": decision_metadata["decision_test_case"],
                        "autonomy_level": decision_metadata["autonomy_level"],
                        "policy_version": decision_metadata["policy_version"],
                    },
                )

            else:
                old = {
                    "abandoned_carts": buyer.get("abandoned_carts", 0),
                    "carts_count": product.get("carts_count", 0),
                }
                self.db["buyers"].update_one(
                    {"_id": buyer["_id"]},
                    {"$inc": {"abandoned_carts": 1}, "$set": {"last_active": now}},
                )
                self.db["products"].update_one(
                    {"_id": product["_id"]},
                    {"$inc": {"carts_count": 1}, "$set": {"updated_at": now}},
                )
                self._log_action(
                    agent,
                    "abandoned_cart",
                    "buyers",
                    buyer["_id"],
                    old,
                    {
                        "abandoned_carts": old["abandoned_carts"] + 1,
                        "carts_count": old["carts_count"] + 1,
                    },
                    {"product": product["name"], "buyer": buyer["segment"]},
                )

    def _point_of_sale_agent(self) -> None:
        agent = "Point of Sale Agent"
        terminals = list(self.db["pos_terminals"].find({"status": {"$ne": "Offline"}}))
        if not terminals:
            terminals = list(self.db["pos_terminals"].find({}))
        products = list(self.db["products"].find({"seller_status": "Active", "stock": {"$gt": 0}}))
        buyers = list(self.db["buyers"].find({}))
        if not terminals or not products or not buyers:
            return

        for _ in range(self.random.randint(*POS_SALES_PER_CYCLE)):
            terminal = self.random.choice(terminals)
            product = self.random.choice(products)
            buyer = self.random.choice(buyers)
            fresh_product = self.db["products"].find_one({"_id": product["_id"]})
            if not fresh_product or int(fresh_product.get("stock", 0)) <= 0:
                self._log_action(
                    agent,
                    "pos_checkout",
                    "products",
                    product["_id"],
                    {"stock": product.get("stock", 0)},
                    {"receipt_created": False},
                    {"blocked": "out_of_stock", "terminal": terminal.get("terminal_id")},
                    validation_status="skipped",
                )
                continue

            now = utcnow()
            quantity = min(self.random.randint(1, 3), int(fresh_product.get("stock", 1)))
            amount = round(float(fresh_product.get("price", 1)) * quantity, 2)
            transaction_id = f"txn-pos-{uuid.uuid4().hex[:10]}"
            receipt_id = f"rcpt-{terminal.get('terminal_id', 'pos')}-{uuid.uuid4().hex[:8]}"
            payment_method = self.random.choice(POS_PAYMENT_METHODS)
            scenario_key = self.random.choice(POS_DECISION_SCENARIOS)
            status = "Pending" if scenario_key == "connector_retry" else self.random.choices(["Completed", "Pending"], weights=[94, 6])[0]
            decision_metadata = build_decision_metadata(
                source="agent-pos-sale",
                sequence=transaction_id,
                buyer=buyer,
                product=fresh_product,
                amount=amount,
                quantity=quantity,
                timestamp=now,
                scenario_key=scenario_key,
                suspicious=False,
                status=status,
            )
            decision_metadata["event_type"] = "pos.checkout"
            decision_metadata["channel"] = "store_pos"
            transaction = {
                "_id": transaction_id,
                "transaction_id": transaction_id,
                "buyer_id": buyer["buyer_id"],
                "buyer_name": buyer["name"],
                "seller_id": fresh_product["seller_id"],
                "product_id": fresh_product["product_id"],
                "product_name": fresh_product["name"],
                "quantity": quantity,
                "amount": amount,
                "status": status,
                "suspicious": False,
                "risk_score": buyer.get("risk_score", 0.1),
                "inventory_applied": False,
                "inventory_quantity_applied": 0,
                "points_applied": False,
                "sales_channel": "Point of Sale",
                "payment_method": payment_method,
                "pos_terminal_id": terminal["terminal_id"],
                "store_name": terminal["store_name"],
                "store_city": terminal.get("city"),
                "register_name": terminal.get("register_name"),
                "cashier_name": terminal.get("cashier_name"),
                "receipt_id": receipt_id,
                "timestamp": now,
                **decision_metadata,
            }
            self.db["transactions"].insert_one(transaction)

            buyer_update = {"$set": {"last_active": now, "status": "Active"}}
            if status in {"Completed", "Pending"}:
                buyer_update["$inc"] = {"orders_count": 1, "lifetime_value": amount}
            self.db["buyers"].update_one({"_id": buyer["_id"]}, buyer_update)

            seller_update = {"$set": {"updated_at": now}}
            if status in {"Completed", "Pending"}:
                seller_update["$inc"] = {"revenue": amount}
                if status == "Pending":
                    seller_update["$inc"]["pending_orders"] = 1
            self.db["sellers"].update_one({"_id": fresh_product["seller_id"]}, seller_update)

            old_queue = max(0, int(terminal.get("queue_depth", 0)))
            new_queue = max(0, old_queue + self.random.choice([-2, -1, 0, 1, 2]))
            previous_orders = max(0, int(terminal.get("total_orders", 0)))
            previous_revenue = max(0.0, float(terminal.get("total_revenue", 0)))
            next_total_orders = previous_orders + 1
            next_total_revenue = round(previous_revenue + amount, 2)
            terminal_update = {
                "$inc": {
                    "today_orders": 1,
                    "today_revenue": amount,
                    "total_orders": 1,
                    "total_revenue": amount,
                    f"payment_mix.{payment_method}": 1,
                },
                "$set": {
                    "status": "Busy" if new_queue >= 5 else "Open",
                    "queue_depth": new_queue,
                    "average_ticket": round(next_total_revenue / max(1, next_total_orders), 2),
                    "last_sale_at": now,
                    "updated_at": now,
                },
            }
            if payment_method == "Cash":
                terminal_update["$inc"]["cash_drawer_balance"] = amount
            self.db["pos_terminals"].update_one({"_id": terminal["_id"]}, terminal_update)
            terminal["queue_depth"] = new_queue
            terminal["status"] = "Busy" if new_queue >= 5 else "Open"
            terminal["today_orders"] = int(terminal.get("today_orders", 0)) + 1
            terminal["today_revenue"] = round(float(terminal.get("today_revenue", 0)) + amount, 2)
            terminal["total_orders"] = next_total_orders
            terminal["total_revenue"] = next_total_revenue

            self._log_action(
                agent,
                "pos_checkout",
                "transactions",
                transaction_id,
                {"terminal": terminal["terminal_id"], "queue_depth": old_queue},
                {
                    "amount": amount,
                    "quantity": quantity,
                    "status": status,
                    "payment_method": payment_method,
                    "queue_depth": new_queue,
                },
                {
                    "terminal": terminal["terminal_id"],
                    "store": terminal["store_name"],
                    "receipt": receipt_id,
                    "product": fresh_product["name"],
                    "decision_id": decision_metadata["decision_id"],
                    "decision_test_case": decision_metadata["decision_test_case"],
                    "autonomy_level": decision_metadata["autonomy_level"],
                    "policy_version": decision_metadata["policy_version"],
                },
            )

    def _inventory_agent(self) -> None:
        agent = "Inventory Agent"
        pending_transactions = list(
            self.db["transactions"].find(
                {"inventory_applied": False, "status": {"$in": ["Completed", "Pending"]}},
                sort=[("timestamp", 1)],
                limit=INVENTORY_PROCESS_LIMIT,
            )
        )
        for transaction in pending_transactions:
            product = self.db["products"].find_one({"_id": transaction["product_id"]})
            if not product:
                continue
            requested_quantity = int(transaction.get("quantity", 1))
            available = max(0, int(product.get("stock", 0)))
            applied_quantity = min(requested_quantity, available)
            new_stock = max(0, available - applied_quantity)
            new_status = "Low Stock" if new_stock <= int(product.get("low_stock_threshold", 0)) else "Active"
            transaction_status = transaction["status"]
            if applied_quantity == 0:
                transaction_status = "Cancelled"
            elif applied_quantity < requested_quantity:
                transaction_status = "Backordered"

            self.db["products"].update_one(
                {"_id": product["_id"]},
                {
                    "$set": {
                        "stock": new_stock,
                        "status": new_status,
                        "inventory_policy_status": "low_stock_block" if new_status == "Low Stock" else "eligible",
                        "offer_eligible": new_status == "Active"
                        and float(product.get("gross_margin_pct", 1)) >= float(product.get("margin_floor_pct", 0)),
                        "updated_at": utcnow(),
                    },
                    "$inc": {"sold_count": applied_quantity},
                },
            )
            self.db["transactions"].update_one(
                {"_id": transaction["_id"]},
                {
                    "$set": {
                        "inventory_applied": True,
                        "inventory_quantity_applied": applied_quantity,
                        "status": transaction_status,
                    }
                },
            )
            self._log_action(
                agent,
                "inventory_sale",
                "products",
                product["_id"],
                {"stock": available, "sold_count": product.get("sold_count", 0)},
                {"stock": new_stock, "sold_count": product.get("sold_count", 0) + applied_quantity},
                {"transaction": transaction["_id"], "requested": requested_quantity},
            )

        low_products = list(
            self.db["products"].find(
                {"$or": [{"status": {"$ne": "Low Stock"}}, {"stock": {"$lte": 20}}]},
                limit=LOW_STOCK_SCAN_LIMIT,
            )
        )
        for product in low_products:
            stock = int(product.get("stock", 0))
            threshold = int(product.get("low_stock_threshold", 0))
            if stock <= threshold and product.get("status") != "Low Stock":
                self.db["products"].update_one(
                    {"_id": product["_id"]},
                    {
                        "$set": {
                            "status": "Low Stock",
                            "inventory_policy_status": "low_stock_block",
                            "offer_eligible": False,
                            "updated_at": utcnow(),
                        }
                    },
                )
                self._log_action(
                    agent,
                    "low_stock",
                    "products",
                    product["_id"],
                    {"status": product.get("status"), "stock": stock},
                    {"status": "Low Stock", "stock": stock},
                    {"threshold": threshold},
                )

        restock_candidates = list(self.db["products"].find({"status": "Low Stock"}))
        if restock_candidates and self.random.random() < 0.65:
            product = self.random.choice(restock_candidates)
            old_stock = max(0, int(product.get("stock", 0)))
            restock_units = self.random.randint(12, 36)
            new_stock = old_stock + restock_units
            self.db["products"].update_one(
                {"_id": product["_id"]},
                {
                    "$set": {
                        "stock": new_stock,
                        "status": "Active",
                        "inventory_policy_status": "eligible",
                        "offer_eligible": float(product.get("gross_margin_pct", 1))
                        >= float(product.get("margin_floor_pct", 0)),
                        "updated_at": utcnow(),
                    }
                },
            )
            self._log_action(
                agent,
                "restock",
                "products",
                product["_id"],
                {"stock": old_stock, "status": product.get("status")},
                {"stock": new_stock, "status": "Active"},
                {"restock_units": restock_units},
            )

    def _seller_agent(self) -> None:
        agent = "Seller Agent"
        sellers = list(self.db["sellers"].find({}))
        if not sellers:
            return
        for seller in self.random.sample(sellers, k=min(SELLER_UPDATES_PER_CYCLE, len(sellers))):
            old = {
                "rating": seller.get("rating"),
                "fulfillment_status": seller.get("fulfillment_status"),
                "pending_orders": seller.get("pending_orders", 0),
                "active": seller.get("active", True),
                "connector_health": seller.get("connector_health"),
                "retry_queue_depth": seller.get("retry_queue_depth", 0),
            }
            pending_orders = max(0, int(seller.get("pending_orders", 0)) - self.random.choice([0, 0, 1]))
            fulfillment_rate = clamp(float(seller.get("fulfillment_rate", 95)) + self.random.uniform(-1.2, 1.4), 80, 99.8)
            rating = clamp(float(seller.get("rating", 4.5)) + self.random.uniform(-0.03, 0.04), 3.6, 5.0)
            if pending_orders >= 8 or fulfillment_rate < 88:
                fulfillment_status = "At Risk"
                connector_health = "Degraded"
            elif pending_orders >= 4:
                fulfillment_status = "Busy"
                connector_health = self.random.choice(["Healthy", "Retrying"])
            else:
                fulfillment_status = "Healthy"
                connector_health = "Healthy"
            active = fulfillment_status != "At Risk" or self.random.random() > 0.15
            retry_queue_depth = 0 if connector_health == "Healthy" else max(1, int(seller.get("retry_queue_depth", 0)) + 1)

            new = {
                "rating": round(rating, 2),
                "fulfillment_status": fulfillment_status,
                "fulfillment_rate": round(fulfillment_rate, 1),
                "pending_orders": pending_orders,
                "active": active,
                "connector_health": connector_health,
                "last_sync_status": "Synced" if connector_health == "Healthy" else "Retrying",
                "latency_ms": self.random.randint(60, 520 if connector_health != "Healthy" else 240),
                "error_rate_pct": round(self.random.uniform(0.1, 2.4 if connector_health == "Healthy" else 8.5), 2),
                "retry_queue_depth": retry_queue_depth,
            }
            self.db["sellers"].update_one({"_id": seller["_id"]}, {"$set": {**new, "updated_at": utcnow()}})
            self.db["products"].update_many(
                {"seller_id": seller["seller_id"]},
                {"$set": {"seller_status": "Active" if active else "Inactive"}},
            )
            self._log_action(agent, "seller_update", "sellers", seller["_id"], old, new, {"seller": seller["name"]})

        if self.random.random() < CATALOG_LAUNCH_PROBABILITY:
            active_sellers = [seller for seller in sellers if seller.get("active", True)]
            launch_count = min(self.random.randint(*CATALOG_LAUNCHES_PER_CYCLE), len(active_sellers))
            for seller in self.random.sample(active_sellers, k=launch_count):
                self._launch_catalog_listing(seller)

    def _launch_catalog_listing(self, seller: dict[str, Any]) -> None:
        category = seller.get("category_focus", "Lifestyle")
        product_id = f"prd-agent-{uuid.uuid4().hex[:10]}"
        prefix = self.random.choice(CATALOG_LAUNCH_TERMS.get(category, ["Swift"]))
        product_type = self.random.choice(CATALOG_LAUNCH_PRODUCTS.get(category, ["Marketplace Item"]))
        name = f"{prefix}{self.random.randint(10, 99)} {product_type}"
        base_price = round(self.random.uniform(399, 4999), 2)
        discount_pct = self.random.choice([0, 0, 5, 8, 10, 12, 15])
        price = round(max(1.0, base_price * (1 - discount_pct / 100)), 2)
        stock = self.random.randint(18, 140)
        low_stock_threshold = self.random.randint(8, 18)
        gross_margin_pct = round(self.random.uniform(0.2, 0.5), 3)
        margin_floor_pct = round(self.random.uniform(0.14, 0.24), 3)
        existing = self.db["products"].find_one({"category": category, "image_url": {"$ne": None}})
        image_url = (existing or {}).get("image_url", "/images/products/product.svg")
        now = utcnow()
        product = {
            "_id": product_id,
            "product_id": product_id,
            "name": name,
            "slug": slugify(name),
            "category": category,
            "base_price": float(base_price),
            "price": price,
            "discount_pct": discount_pct,
            "stock": stock,
            "low_stock_threshold": low_stock_threshold,
            "sold_count": self.random.randint(0, 12),
            "views_count": self.random.randint(35, 180),
            "carts_count": self.random.randint(3, 38),
            "brand": seller.get("name", "SwiftCart").split()[0],
            "rating": round(self.random.uniform(4.0, 4.8), 1),
            "review_count": self.random.randint(25, 650),
            "delivery_badge": self.random.choice(
                [
                    "New arrival",
                    "Free delivery by tomorrow",
                    "Cashpoints launch bonus",
                    "Limited launch deal",
                ]
            ),
            "promotion": self.random.choice(["New launch", "Launch saver", "Cashpoints bonus"]) if discount_pct else "",
            "gross_margin_pct": gross_margin_pct,
            "margin_floor_pct": margin_floor_pct,
            "promotion_budget_remaining": self.random.randint(25000, 120000),
            "discount_exposure_remaining": self.random.randint(2500, 18000),
            "offer_eligible": stock > low_stock_threshold and gross_margin_pct >= margin_floor_pct,
            "campaign_id": f"cmp-agent-{category.lower()}-{self.random.randint(100, 999)}",
            "partner_liability_pct": round(self.random.uniform(0.15, 0.58), 2),
            "inventory_policy_status": "eligible",
            "decision_context": {
                "commercial_domain": "agent_catalog_launch",
                "policy_version": DECISION_POLICY_VERSION,
                "margin_owner": "Category Finance",
                "campaign_owner": "Seller Growth",
                "evidence_fields": ["price", "stock", "discount_pct", "gross_margin_pct"],
            },
            "status": "Active",
            "seller_id": seller["seller_id"],
            "seller_status": "Active",
            "image_url": image_url,
            "created_at": now,
            "updated_at": now,
        }
        self.db["products"].insert_one(product)
        self.db["sellers"].update_one(
            {"_id": seller["_id"]},
            {"$inc": {"product_count": 1}, "$set": {"updated_at": now}},
        )
        self._log_action(
            "Seller Agent",
            "catalog_launch",
            "products",
            product_id,
            {},
            {"name": name, "category": category, "stock": stock, "price": price},
            {
                "seller": seller.get("name"),
                "category": category,
                "autonomy_level": "Level 3 - Bounded Autonomy",
                "policy_version": DECISION_POLICY_VERSION,
                "decision_test_case": "rollback_available",
            },
        )

    def _cashpoints_agent(self) -> None:
        agent = "Cashpoints Agent"
        reward_transactions = list(
            self.db["transactions"].find(
                {
                    "status": "Completed",
                    "points_applied": False,
                    "inventory_quantity_applied": {"$gt": 0},
                },
                sort=[("timestamp", 1)],
                limit=REWARD_PROCESS_LIMIT,
            )
        )
        for transaction in reward_transactions:
            buyer = self.db["buyers"].find_one({"_id": transaction["buyer_id"]})
            if not buyer:
                continue
            old_balance = max(0, int(buyer.get("cashpoints_balance", 0)))
            points = max(1, int(float(transaction.get("amount", 0)) * 0.05))
            new_balance = old_balance + points
            ledger_id = f"cp-{uuid.uuid4().hex[:10]}"
            ledger_metadata = build_ledger_metadata(
                source="agent-points-earned",
                sequence=ledger_id,
                buyer=buyer,
                points=points,
                timestamp=utcnow(),
                scenario_key=transaction.get("decision_test_case", "loyalty_reward_allowed"),
                suspicious=False,
            )
            ledger_metadata["source_decision_id"] = transaction.get("decision_id")
            self.db["buyers"].update_one({"_id": buyer["_id"]}, {"$set": {"cashpoints_balance": new_balance}})
            self.db["transactions"].update_one({"_id": transaction["_id"]}, {"$set": {"points_applied": True}})
            self.db["cashpoints_ledger"].insert_one(
                {
                    "_id": ledger_id,
                    "ledger_id": ledger_id,
                    "buyer_id": buyer["buyer_id"],
                    "buyer_name": buyer["name"],
                    "transaction_id": transaction["transaction_id"],
                    "points": points,
                    "balance_after": new_balance,
                    "entry_type": "Earned",
                    "reason": "Purchase reward",
                    "suspicious": False,
                    "timestamp": utcnow(),
                    **ledger_metadata,
                }
            )
            self._log_action(
                agent,
                "points_earned",
                "cashpoints_ledger",
                ledger_id,
                {"cashpoints_balance": old_balance},
                {"cashpoints_balance": new_balance, "points": points},
                {
                    "transaction": transaction["_id"],
                    "decision_id": ledger_metadata["decision_id"],
                    "decision_test_case": ledger_metadata["decision_test_case"],
                    "autonomy_level": ledger_metadata["autonomy_level"],
                    "policy_version": ledger_metadata["policy_version"],
                },
            )

        if self.random.random() < 0.8:
            buyers = list(self.db["buyers"].find({"cashpoints_balance": {"$gt": 120}}))
            if buyers:
                for buyer in self.random.sample(buyers, k=min(self.random.randint(1, 3), len(buyers))):
                    old_balance = max(0, int(buyer.get("cashpoints_balance", 0)))
                    redeem_points = min(old_balance, self.random.randint(35, 140))
                    new_balance = max(0, old_balance - redeem_points)
                    ledger_id = f"cp-{uuid.uuid4().hex[:10]}"
                    ledger_metadata = build_ledger_metadata(
                        source="agent-points-redeemed",
                        sequence=ledger_id,
                        buyer=buyer,
                        points=-redeem_points,
                        timestamp=utcnow(),
                        scenario_key="loyalty_reward_allowed",
                        suspicious=False,
                    )
                    self.db["buyers"].update_one({"_id": buyer["_id"]}, {"$set": {"cashpoints_balance": new_balance}})
                    self.db["cashpoints_ledger"].insert_one(
                        {
                            "_id": ledger_id,
                            "ledger_id": ledger_id,
                            "buyer_id": buyer["buyer_id"],
                            "buyer_name": buyer["name"],
                            "transaction_id": None,
                            "points": -redeem_points,
                            "balance_after": new_balance,
                            "entry_type": "Redeemed",
                            "reason": "Checkout discount redemption",
                            "suspicious": False,
                            "timestamp": utcnow(),
                            **ledger_metadata,
                        }
                    )
                    self._log_action(
                        agent,
                        "points_redeemed",
                        "cashpoints_ledger",
                        ledger_id,
                        {"cashpoints_balance": old_balance},
                        {"cashpoints_balance": new_balance, "points": -redeem_points},
                        {
                            "buyer": buyer["segment"],
                            "decision_id": ledger_metadata["decision_id"],
                            "decision_test_case": ledger_metadata["decision_test_case"],
                            "autonomy_level": ledger_metadata["autonomy_level"],
                            "policy_version": ledger_metadata["policy_version"],
                        },
                    )

    def _pricing_promotion_agent(self) -> None:
        agent = "Pricing/Promotion Agent"
        config = self.get_config()
        max_discount_pct = int(config.get("max_discount_pct", 25))
        products = list(self.db["products"].find({"seller_status": "Active"}))
        if not products:
            return
        for product in self.random.sample(products, k=min(self.random.randint(*PROMOTION_UPDATES_PER_CYCLE), len(products))):
            old = {
                "price": product.get("price"),
                "discount_pct": product.get("discount_pct", 0),
                "promotion": product.get("promotion", ""),
            }
            if self.random.random() < 0.3:
                discount_pct = 0
                promotion = ""
            else:
                discount_pct = self.random.choice([5, 7, 10, 12, 15, 18, max_discount_pct])
                discount_pct = min(max_discount_pct, max(0, int(discount_pct)))
                promotion = self.random.choice(["Flash saver", "Cart booster", "Weekend lift", "Loyalty nudge"])
            margin_floor_breached = float(product.get("gross_margin_pct", 1)) < float(product.get("margin_floor_pct", 0))
            pricing_case = "margin_floor_block" if margin_floor_breached and discount_pct > 0 else "loyalty_reward_allowed"
            if pricing_case == "margin_floor_block":
                discount_pct = 0
                promotion = ""
            price = round(max(1.0, float(product.get("base_price", product.get("price", 1))) * (1 - discount_pct / 100)), 2)
            decision_id = f"dec-price-{uuid.uuid4().hex[:10]}"
            self.db["products"].update_one(
                {"_id": product["_id"]},
                {
                    "$set": {
                        "discount_pct": discount_pct,
                        "price": price,
                        "promotion": promotion,
                        "pricing_policy": {
                            "decision_id": decision_id,
                            "policy_version": DECISION_POLICY_VERSION,
                            "decision_test_case": pricing_case,
                            "max_discount_pct": max_discount_pct,
                            "margin_floor_pct": product.get("margin_floor_pct"),
                            "result": "blocked" if pricing_case == "margin_floor_block" else "passed",
                        },
                        "last_pricing_decision": {
                            "decision_id": decision_id,
                            "autonomy_level": "Level 3 - Bounded Autonomy",
                            "action_graph_status": "Completed",
                            "rollback_available": True,
                        },
                        "updated_at": utcnow(),
                    }
                },
            )
            self._log_action(
                agent,
                "discount_update",
                "products",
                product["_id"],
                old,
                {"price": price, "discount_pct": discount_pct, "promotion": promotion},
                {
                    "max_discount_pct": max_discount_pct,
                    "product": product["category"],
                    "decision_id": decision_id,
                    "decision_test_case": pricing_case,
                    "autonomy_level": "Level 3 - Bounded Autonomy",
                    "policy_version": DECISION_POLICY_VERSION,
                },
            )

    def _fraud_anomaly_agent(self) -> None:
        agent = "Fraud/Anomaly Agent"
        if self.random.random() < 0.9:
            buyers = list(self.db["buyers"].find({}))
            products = list(self.db["products"].find({}))
            if buyers and products:
                for _ in range(self.random.randint(*FRAUD_TRANSACTIONS_PER_CYCLE)):
                    buyer = self.random.choice(buyers)
                    product = self.random.choice(products)
                    risk_score = round(clamp(float(buyer.get("risk_score", 0.2)) + self.random.uniform(0.25, 0.48), 0, 0.99), 2)
                    transaction_id = f"txn-flag-{uuid.uuid4().hex[:10]}"
                    quantity = self.random.randint(3, 8)
                    amount = round(float(product.get("price", 1)) * quantity, 2)
                    decision_metadata = build_decision_metadata(
                        source="agent-fraud",
                        sequence=transaction_id,
                        buyer=buyer,
                        product=product,
                        amount=amount,
                        quantity=quantity,
                        timestamp=utcnow(),
                        scenario_key="fraud_redemption_review",
                        suspicious=True,
                        status="Flagged",
                    )
                    transaction = {
                        "_id": transaction_id,
                        "transaction_id": transaction_id,
                        "buyer_id": buyer["buyer_id"],
                        "buyer_name": buyer["name"],
                        "seller_id": product["seller_id"],
                        "product_id": product["product_id"],
                        "product_name": product["name"],
                        "quantity": quantity,
                        "amount": amount,
                        "status": "Flagged",
                        "suspicious": True,
                        "risk_score": risk_score,
                        "inventory_applied": True,
                        "inventory_quantity_applied": 0,
                        "points_applied": True,
                        "timestamp": utcnow(),
                        **decision_metadata,
                    }
                    self.db["transactions"].insert_one(transaction)
                    self.db["buyers"].update_one({"_id": buyer["_id"]}, {"$set": {"risk_score": risk_score}})
                    self._log_action(
                        agent,
                        "suspicious_transaction",
                        "transactions",
                        transaction_id,
                        {"risk_score": buyer.get("risk_score")},
                        {"risk_score": risk_score, "status": "Flagged", "amount": amount},
                        {
                            "product": product["category"],
                            "buyer": buyer["segment"],
                            "decision_id": decision_metadata["decision_id"],
                            "decision_test_case": decision_metadata["decision_test_case"],
                            "autonomy_level": decision_metadata["autonomy_level"],
                            "policy_version": decision_metadata["policy_version"],
                        },
                        validation_status="flagged",
                    )

        if self.random.random() < 0.7:
            buyers = list(self.db["buyers"].find({"cashpoints_balance": {"$gt": 250}}))
            if not buyers:
                return
            for buyer in self.random.sample(buyers, k=min(self.random.randint(*SUSPICIOUS_REDEMPTIONS_PER_CYCLE), len(buyers))):
                old_balance = max(0, int(buyer.get("cashpoints_balance", 0)))
                redeem_points = min(old_balance, self.random.randint(180, 420))
                new_balance = max(0, old_balance - redeem_points)
                ledger_id = f"cp-flag-{uuid.uuid4().hex[:10]}"
                ledger_metadata = build_ledger_metadata(
                    source="agent-suspicious-redemption",
                    sequence=ledger_id,
                    buyer=buyer,
                    points=-redeem_points,
                    timestamp=utcnow(),
                    scenario_key="fraud_redemption_review",
                    suspicious=True,
                )
                self.db["buyers"].update_one(
                    {"_id": buyer["_id"]},
                    {"$set": {"cashpoints_balance": new_balance, "risk_score": clamp(buyer.get("risk_score", 0.2) + 0.08, 0, 0.99)}},
                )
                self.db["cashpoints_ledger"].insert_one(
                    {
                        "_id": ledger_id,
                        "ledger_id": ledger_id,
                        "buyer_id": buyer["buyer_id"],
                        "buyer_name": buyer["name"],
                        "transaction_id": None,
                        "points": -redeem_points,
                        "balance_after": new_balance,
                        "entry_type": "Flagged Redemption",
                        "reason": "Unusual high-value redemption",
                        "suspicious": True,
                        "timestamp": utcnow(),
                        **ledger_metadata,
                    }
                )
                self._log_action(
                    agent,
                    "suspicious_redemption",
                    "cashpoints_ledger",
                    ledger_id,
                    {"cashpoints_balance": old_balance},
                    {"cashpoints_balance": new_balance, "points": -redeem_points},
                    {
                        "buyer": buyer["segment"],
                        "decision_id": ledger_metadata["decision_id"],
                        "decision_test_case": ledger_metadata["decision_test_case"],
                        "autonomy_level": ledger_metadata["autonomy_level"],
                        "policy_version": ledger_metadata["policy_version"],
                    },
                    validation_status="flagged",
                )

    def _metrics_agent(self) -> None:
        old = self.db["business_metrics"].find_one({"_id": "current"}) or {}
        new = recalculate_and_store_metrics(self.db)
        self._log_action(
            "Metrics Agent",
            "metrics_refresh",
            "business_metrics",
            "current",
            {
                "total_revenue": old.get("total_revenue"),
                "orders_today": old.get("orders_today"),
                "suspicious_transactions": old.get("suspicious_transactions"),
                "pos_orders_today": old.get("pos_orders_today"),
            },
            {
                "total_revenue": new.get("total_revenue"),
                "orders_today": new.get("orders_today"),
                "suspicious_transactions": new.get("suspicious_transactions"),
                "pos_orders_today": new.get("pos_orders_today"),
            },
            {"source": "collections"},
        )

    def _choose_purchase_scenario(self, buyer: dict[str, Any], product: dict[str, Any], amount: float) -> str:
        if buyer.get("consent_status") == "opted_out" and self.random.random() < 0.35:
            return "consent_personalization_block"
        if int(product.get("stock", 0)) <= int(product.get("low_stock_threshold", 0)) and self.random.random() < 0.5:
            return "inventory_low_stock_block"
        if float(product.get("gross_margin_pct", 1)) < float(product.get("margin_floor_pct", 0)) and self.random.random() < 0.5:
            return "margin_floor_block"
        if amount >= 12000 or self.random.random() < 0.12:
            return "approval_required_high_value"
        return self.random.choice(
            [
                "loyalty_reward_allowed",
                "loyalty_reward_allowed",
                "connector_retry",
                "holdout_experiment",
                "rollback_available",
                "deterministic_fallback",
            ]
        )

    def _set_config(self, values: dict[str, Any]) -> None:
        self.db["simulation_config"].update_one({"_id": "main"}, {"$set": values}, upsert=True)

    def _next_interval(self, speed: str) -> int:
        low, high = SPEED_RANGES.get(speed, SPEED_RANGES["five_minute"])
        if low == high == 300:
            return self.interval_seconds
        return self.random.randint(low, high)

    def _log_action(
        self,
        agent_name: str,
        action_type: str,
        affected_collection: str,
        affected_id: str,
        old_value: dict,
        new_value: dict,
        context: dict[str, Any] | None = None,
        validation_status: str = "passed",
    ) -> None:
        timestamp = utcnow()
        context = context or {}
        reason = self.reasons.explain(agent_name, action_type, context)
        document = {
            "_id": f"log-{uuid.uuid4().hex[:12]}",
            "agent_name": agent_name,
            "action_type": action_type,
            "affected_collection": affected_collection,
            "affected_id": affected_id,
            "old_value": serialize_value(old_value),
            "new_value": serialize_value(new_value),
            "reason": reason,
            "reason_provider": self.reasons.last_provider,
            "validation_status": validation_status,
            "timestamp": timestamp,
        }
        for key in ("decision_id", "decision_test_case", "autonomy_level", "policy_version", "request_id"):
            if context.get(key):
                document[key] = serialize_value(context[key])
        if context.get("evidence_refs"):
            document["evidence_refs"] = serialize_value(context["evidence_refs"])
        self.db["agent_activity_log"].insert_one(document)
