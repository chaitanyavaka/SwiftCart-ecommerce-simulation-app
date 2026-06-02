from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Any


FALLBACK_REASONS = {
    "view": "Buyer browsing pattern matched normal category interest.",
    "cart": "Buyer added an item after repeated product engagement.",
    "purchase": "Purchase created from simulated buyer demand.",
    "abandoned_cart": "Cart was abandoned after price and stock checks.",
    "inventory_sale": "Stock adjusted after a simulated order was accepted.",
    "restock": "Product restocked because available units reached a marketplace threshold.",
    "low_stock": "Product marked low stock after inventory validation.",
    "seller_update": "Seller performance refreshed from simulated fulfillment signals.",
    "catalog_launch": "Seller launched a new listing after marketplace availability checks.",
    "points_earned": "Cashpoints issued after a completed purchase.",
    "points_redeemed": "Buyer redeemed points within available balance.",
    "discount_update": "Promotion adjusted within configured discount limits.",
    "suspicious_transaction": "Transaction flagged because risk signals exceeded marketplace norms.",
    "suspicious_redemption": "Redemption flagged because point usage was unusually high.",
    "metrics_refresh": "Dashboard metrics recalculated from current collections.",
    "simulation": "Simulation control updated by the admin.",
}


class ReasonGenerator:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model or "llama-3.1-8b-instant"
        self.last_provider = "fallback"
        self._client = None
        if api_key:
            try:
                from groq import Groq

                self._client = Groq(api_key=api_key, timeout=4.0)
            except Exception:
                self._client = None

    def explain(self, agent_name: str, action_type: str, context: dict[str, Any] | None = None) -> str:
        self.last_provider = "fallback"
        if self._client:
            try:
                prompt = (
                    "Write one short operational reason, under 18 words, for this ecommerce "
                    f"simulation action. Agent: {agent_name}. Action: {action_type}. "
                    f"Context: {context or {}}"
                )
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=40,
                )
                content = response.choices[0].message.content.strip()
                if content:
                    self.last_provider = "groq_sdk"
                    return content[:180]
            except Exception:
                pass
        if self.api_key:
            content = self._explain_with_rest(agent_name, action_type, context or {})
            if content:
                self.last_provider = "groq_rest"
                return content

        fallback = FALLBACK_REASONS.get(action_type, FALLBACK_REASONS["simulation"])
        if context:
            digest = hashlib.sha1(str(sorted(context.items())).encode("utf-8")).hexdigest()[:4]
            return f"{fallback} Ref {digest}."
        return fallback

    def _explain_with_rest(self, agent_name: str, action_type: str, context: dict[str, Any]) -> str | None:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Write one short operational reason, under 18 words, for this ecommerce "
                        f"automation action. Agent: {agent_name}. Action: {action_type}. Context: {context}"
                    ),
                }
            ],
            "temperature": 0.2,
            "max_tokens": 40,
        }
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            return content[:180] if content else None
        except (KeyError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None
