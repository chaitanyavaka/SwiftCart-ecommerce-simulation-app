from __future__ import annotations

import unittest

from ecommerce_demo import create_app
from ecommerce_demo.decision_fixtures import DECISION_TEST_CASE_KEYS


class EcommerceDemoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "USE_MEMORY_DB": True,
                "AUTO_SEED": True,
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD": "demo123",
                "SIMULATION_RANDOM_SEED": "tests",
            }
        )
        self.client = self.app.test_client()
        self.db = self.app.extensions["demo_db"]
        self.engine = self.app.extensions["simulation_engine"]

    def login(self):
        return self.client.post(
            "/login",
            data={"username": "admin", "password": "demo123"},
            follow_redirects=True,
        )

    def test_app_starts(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SwiftCart", response.data)

    def test_seed_data_loads(self):
        self.assertGreaterEqual(self.db["products"].count_documents({}), 20)
        self.assertEqual(self.db["buyers"].count_documents({}), 20)
        self.assertGreaterEqual(self.db["sellers"].count_documents({}), 5)
        self.assertGreater(self.db["transactions"].count_documents({}), 0)
        self.assertGreater(self.db["cashpoints_ledger"].count_documents({}), 0)

    def test_decision_test_fixture_data_is_seeded(self):
        transactions = list(self.db["transactions"].find({}))
        buyers = list(self.db["buyers"].find({}))
        products = list(self.db["products"].find({}))
        sellers = list(self.db["sellers"].find({}))
        cases = {txn.get("decision_test_case") for txn in transactions}
        self.assertTrue(set(DECISION_TEST_CASE_KEYS).issubset(cases))
        sample = transactions[0]
        self.assertIn("decision_id", sample)
        self.assertIn("policy_checks", sample)
        self.assertIn("action_graph", sample)
        self.assertIn("execution_receipt", sample)
        self.assertIn("decision_context_pack", sample)
        self.assertTrue(any(buyer.get("consent_status") for buyer in buyers))
        self.assertTrue(any(product.get("gross_margin_pct") for product in products))
        self.assertTrue(any(seller.get("connector_id") for seller in sellers))

    def test_existing_api_surface_only(self):
        self.login()
        for endpoint in (
            "/api/products",
            "/api/buyers",
            "/api/sellers",
            "/api/transactions",
            "/api/cashpoints",
            "/api/metrics",
            "/api/agent-activity",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 200)
        self.assertEqual(self.client.get("/api/agents").status_code, 404)
        self.assertEqual(self.client.post("/api/agents/all/run").status_code, 404)

    def test_inventory_never_goes_negative(self):
        for _ in range(30):
            self.engine.run_cycle()
        products = list(self.db["products"].find({}))
        self.assertTrue(products)
        self.assertTrue(all(product["stock"] >= 0 for product in products))

    def test_cashpoints_never_go_negative(self):
        for _ in range(30):
            self.engine.run_cycle()
        buyers = list(self.db["buyers"].find({}))
        ledger = list(self.db["cashpoints_ledger"].find({}))
        self.assertTrue(all(buyer["cashpoints_balance"] >= 0 for buyer in buyers))
        self.assertTrue(all(entry["balance_after"] >= 0 for entry in ledger))

    def test_discounts_stay_within_limit(self):
        max_discount = self.engine.get_config()["max_discount_pct"]
        for _ in range(20):
            self.engine.run_cycle()
        products = list(self.db["products"].find({}))
        self.assertTrue(all(0 <= product["discount_pct"] <= max_discount for product in products))
        self.assertTrue(all(product["price"] > 0 for product in products))

    def test_transactions_are_generated(self):
        before_ids = {txn["_id"] for txn in self.db["transactions"].find({})}
        before = len(before_ids)
        for _ in range(20):
            self.engine.run_cycle()
        transactions = list(self.db["transactions"].find({}))
        after = len(transactions)
        generated = [txn for txn in transactions if txn["_id"] not in before_ids]
        self.assertGreater(after, before)
        self.assertTrue(generated)
        self.assertTrue(all(txn.get("decision_id") for txn in generated))
        self.assertTrue(all(txn.get("decision_context_pack") for txn in generated))

    def test_agent_actions_are_logged(self):
        before = self.db["agent_activity_log"].count_documents({})
        self.engine.run_cycle()
        after = self.db["agent_activity_log"].count_documents({})
        self.assertGreater(after, before)

    def test_reset_demo_data_works(self):
        self.login()
        self.db["products"].update_one({"_id": "prd-001"}, {"$set": {"stock": 0, "status": "Low Stock"}})
        response = self.client.post("/api/admin/simulation/reset")
        self.assertEqual(response.status_code, 200)
        product = self.db["products"].find_one({"_id": "prd-001"})
        self.assertGreater(product["stock"], 0)
        self.assertEqual(self.engine.get_config()["running"], False)


if __name__ == "__main__":
    unittest.main()
