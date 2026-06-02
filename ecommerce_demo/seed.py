from __future__ import annotations

import random
from datetime import timedelta

from .metrics import recalculate_and_store_metrics
from .decision_fixtures import (
    DECISION_POLICY_VERSION,
    DECISION_TEST_CASE_KEYS,
    build_decision_metadata,
    build_ledger_metadata,
    scenario_for_index,
)
from .utils import slugify, utcnow


COLLECTIONS = [
    "buyers",
    "sellers",
    "products",
    "transactions",
    "pos_terminals",
    "cashpoints_ledger",
    "agent_activity_log",
    "simulation_config",
    "business_metrics",
]


DATASET_VERSION = 9


SELLERS = [
    ("sel-001", "Northstar Home Goods", "Home"),
    ("sel-002", "Volt & Thread", "Electronics"),
    ("sel-003", "UrbanTrail Outfitters", "Outdoor"),
    ("sel-004", "Glowline Beauty", "Beauty"),
    ("sel-005", "PantryPilot Market", "Grocery"),
    ("sel-006", "StudioArc Living", "Lifestyle"),
    ("sel-007", "KiddoCraft Supply", "Kids"),
]


PRODUCTS = [
    ("AeroPods Lite Earbuds", "Electronics", 2499.0, 74, "sel-002"),
    ("Nimbus Smart Speaker", "Electronics", 5499.0, 28, "sel-002"),
    ("FocusFlow Keyboard", "Electronics", 3299.0, 41, "sel-002"),
    ("PocketCharge Mini Bank", "Electronics", 1499.0, 112, "sel-002"),
    ("PixelView 4K Monitor", "Electronics", 18999.0, 42, "sel-002"),
    ("VoltEdge Gaming Mouse", "Electronics", 1299.0, 98, "sel-002"),
    ("ClearCall Noise Cancelling Headset", "Electronics", 4499.0, 56, "sel-002"),
    ("SnapCam Mini Action Camera", "Electronics", 7999.0, 33, "sel-002"),
    ("StreamDeck Creator Mic", "Electronics", 5999.0, 27, "sel-002"),
    ("NovaTab 10 Tablet", "Electronics", 15999.0, 44, "sel-002"),
    ("RapidCharge USB-C Hub", "Electronics", 2199.0, 88, "sel-002"),
    ("HomeGuard WiFi Camera", "Electronics", 3299.0, 69, "sel-002"),
    ("Bamboo Desk Organizer", "Home", 899.0, 55, "sel-001"),
    ("CloudRest Throw Blanket", "Home", 1799.0, 36, "sel-001"),
    ("Copper Pour-Over Kettle", "Home", 2399.0, 19, "sel-001"),
    ("Linen Storage Cube Set", "Home", 999.0, 63, "sel-001"),
    ("OrthoCloud Memory Pillow", "Home", 1499.0, 84, "sel-001"),
    ("AromaMist Oil Diffuser", "Home", 1299.0, 47, "sel-001"),
    ("StackNest Shoe Rack", "Home", 1999.0, 52, "sel-001"),
    ("ChefMate Ceramic Pan", "Home", 2499.0, 40, "sel-001"),
    ("PureCotton Bedsheet Set", "Home", 2199.0, 72, "sel-001"),
    ("FoldEase Laundry Basket", "Home", 799.0, 91, "sel-001"),
    ("BrightLine LED Strip", "Home", 699.0, 106, "sel-001"),
    ("MarbleTop Serving Tray", "Home", 1199.0, 58, "sel-001"),
    ("TrailCore Daypack", "Outdoor", 2899.0, 31, "sel-003"),
    ("Summit Steel Bottle", "Outdoor", 799.0, 86, "sel-003"),
    ("RainShell Compact Jacket", "Outdoor", 3999.0, 17, "sel-003"),
    ("GripLite Hiking Socks", "Outdoor", 399.0, 145, "sel-003"),
    ("CampGlow Rechargeable Lantern", "Outdoor", 1699.0, 61, "sel-003"),
    ("TerraGrip Trekking Pole Pair", "Outdoor", 2299.0, 39, "sel-003"),
    ("BreezeFit Running Cap", "Outdoor", 499.0, 118, "sel-003"),
    ("TrailChef Mess Kit", "Outdoor", 1399.0, 46, "sel-003"),
    ("AquaTrail Hydration Pack", "Outdoor", 3199.0, 25, "sel-003"),
    ("SunGuard Polarized Sunglasses", "Outdoor", 999.0, 77, "sel-003"),
    ("QuickDry Travel Towel", "Outdoor", 649.0, 132, "sel-003"),
    ("BaseCamp Hammock", "Outdoor", 1799.0, 54, "sel-003"),
    ("HydraSilk Face Serum", "Beauty", 1299.0, 52, "sel-004"),
    ("GlowMatte Sunscreen SPF 50", "Beauty", 699.0, 78, "sel-004"),
    ("CalmClay Mask Duo", "Beauty", 899.0, 45, "sel-004"),
    ("VelvetTint Lip Trio", "Beauty", 799.0, 64, "sel-004"),
    ("RoseDew Toner Mist", "Beauty", 599.0, 95, "sel-004"),
    ("KeratinShine Hair Mask", "Beauty", 999.0, 67, "sel-004"),
    ("AquaGel Night Cream", "Beauty", 1199.0, 43, "sel-004"),
    ("SilkTouch Makeup Brush Set", "Beauty", 1499.0, 51, "sel-004"),
    ("Charcoal Detox Face Wash", "Beauty", 349.0, 142, "sel-004"),
    ("CitrusGlow Vitamin C Drops", "Beauty", 899.0, 83, "sel-004"),
    ("NudeBloom Nail Kit", "Beauty", 699.0, 73, "sel-004"),
    ("DailyShield Body Lotion", "Beauty", 499.0, 116, "sel-004"),
    ("Organic Breakfast Bundle", "Grocery", 1199.0, 58, "sel-005"),
    ("Cold Brew Concentrate Pack", "Grocery", 599.0, 91, "sel-005"),
    ("Artisan Pasta Pantry Kit", "Grocery", 1099.0, 43, "sel-005"),
    ("SpiceRoute Starter Set", "Grocery", 849.0, 67, "sel-005"),
    ("Millet Energy Bar Box", "Grocery", 499.0, 122, "sel-005"),
    ("FarmFresh Almond Pack", "Grocery", 799.0, 88, "sel-005"),
    ("GoldenHoney Squeeze Bottle", "Grocery", 449.0, 76, "sel-005"),
    ("Herbal Tea Sampler", "Grocery", 649.0, 64, "sel-005"),
    ("Protein Crunch Muesli", "Grocery", 549.0, 111, "sel-005"),
    ("Cold Pressed Cooking Oil", "Grocery", 999.0, 53, "sel-005"),
    ("Roasted Trail Mix Jar", "Grocery", 599.0, 87, "sel-005"),
    ("Gourmet Cookie Tin", "Grocery", 749.0, 69, "sel-005"),
    ("StudioLamp Ambient Bar", "Lifestyle", 2199.0, 34, "sel-006"),
    ("Minimalist Wall Clock", "Lifestyle", 1499.0, 26, "sel-006"),
    ("ErgoFlex Laptop Stand", "Lifestyle", 1699.0, 71, "sel-006"),
    ("ZenDesk Cable Tray", "Lifestyle", 899.0, 64, "sel-006"),
    ("MoodLite Bedside Lamp", "Lifestyle", 1299.0, 59, "sel-006"),
    ("UrbanCarry Sling Bag", "Lifestyle", 1899.0, 41, "sel-006"),
    ("DeskZen Planter Trio", "Lifestyle", 699.0, 96, "sel-006"),
    ("FocusBoard Weekly Planner", "Lifestyle", 499.0, 124, "sel-006"),
    ("ComfyWork Footrest", "Lifestyle", 1499.0, 48, "sel-006"),
    ("TravelMate Packing Cubes", "Lifestyle", 999.0, 82, "sel-006"),
    ("SoftGrip Yoga Mat", "Lifestyle", 1199.0, 66, "sel-006"),
    ("AeroBreeze Table Fan", "Lifestyle", 2499.0, 37, "sel-006"),
    ("PuzzleBot STEM Kit", "Kids", 1999.0, 39, "sel-007"),
    ("StoryNest Reading Lamp", "Kids", 1199.0, 48, "sel-007"),
    ("Washable Marker Mega Pack", "Kids", 649.0, 72, "sel-007"),
    ("Adventure Map Floor Puzzle", "Kids", 799.0, 44, "sel-007"),
    ("BuildBuddy Blocks 120pc", "Kids", 1299.0, 68, "sel-007"),
    ("SpaceQuest Board Game", "Kids", 999.0, 57, "sel-007"),
    ("TinyChef Pretend Kitchen Set", "Kids", 2299.0, 31, "sel-007"),
    ("DoodlePad LCD Tablet", "Kids", 699.0, 93, "sel-007"),
    ("Animal Tales Flash Cards", "Kids", 399.0, 136, "sel-007"),
    ("Junior Artist Easel", "Kids", 1799.0, 38, "sel-007"),
    ("RoboRacer Pullback Cars", "Kids", 599.0, 104, "sel-007"),
    ("NumberQuest Puzzle Set", "Kids", 549.0, 89, "sel-007"),
]


PRODUCT_IMAGES = {
    "AeroPods Lite Earbuds": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
    "Nimbus Smart Speaker": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=900&q=80",
    "FocusFlow Keyboard": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
    "PocketCharge Mini Bank": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=900&q=80",
    "Bamboo Desk Organizer": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?auto=format&fit=crop&w=900&q=80",
    "CloudRest Throw Blanket": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e6?auto=format&fit=crop&w=900&q=80",
    "Copper Pour-Over Kettle": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&w=900&q=80",
    "Linen Storage Cube Set": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=900&q=80",
    "TrailCore Daypack": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=80",
    "Summit Steel Bottle": "https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=900&q=80",
    "RainShell Compact Jacket": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
    "GripLite Hiking Socks": "https://images.unsplash.com/photo-1582966772680-860e372bb558?auto=format&fit=crop&w=900&q=80",
    "HydraSilk Face Serum": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=900&q=80",
    "GlowMatte Sunscreen SPF 50": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=900&q=80",
    "CalmClay Mask Duo": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?auto=format&fit=crop&w=900&q=80",
    "VelvetTint Lip Trio": "https://images.unsplash.com/photo-1586495777744-4413f21062fa?auto=format&fit=crop&w=900&q=80",
    "Organic Breakfast Bundle": "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=900&q=80",
    "Cold Brew Concentrate Pack": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=80",
    "Artisan Pasta Pantry Kit": "https://images.unsplash.com/photo-1556761223-4c4282c73f77?auto=format&fit=crop&w=900&q=80",
    "SpiceRoute Starter Set": "https://images.unsplash.com/photo-1532336414038-cf19250c5757?auto=format&fit=crop&w=900&q=80",
    "StudioLamp Ambient Bar": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80",
    "Minimalist Wall Clock": "https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?auto=format&fit=crop&w=900&q=80",
    "PuzzleBot STEM Kit": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=900&q=80",
    "StoryNest Reading Lamp": "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?auto=format&fit=crop&w=900&q=80",
    "Washable Marker Mega Pack": "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?auto=format&fit=crop&w=900&q=80",
    "Adventure Map Floor Puzzle": "https://images.unsplash.com/photo-1618842676088-c4d48a6a7c9d?auto=format&fit=crop&w=900&q=80",
}


CATEGORY_IMAGES = {
    "Electronics": PRODUCT_IMAGES["AeroPods Lite Earbuds"],
    "Home": PRODUCT_IMAGES["Bamboo Desk Organizer"],
    "Outdoor": PRODUCT_IMAGES["TrailCore Daypack"],
    "Beauty": PRODUCT_IMAGES["HydraSilk Face Serum"],
    "Grocery": PRODUCT_IMAGES["Organic Breakfast Bundle"],
    "Lifestyle": PRODUCT_IMAGES["StudioLamp Ambient Bar"],
    "Kids": PRODUCT_IMAGES["PuzzleBot STEM Kit"],
}


PRODUCT_BRANDS = {
    "Electronics": ["boAt", "Noise", "Portronics", "Zebronics"],
    "Home": ["Home Centre", "Solimo", "Wakefit", "Nestasia"],
    "Outdoor": ["Wildcraft", "Decathlon", "Quechua", "Boldfit"],
    "Beauty": ["Minimalist", "Lakme", "Plum", "Mamaearth"],
    "Grocery": ["Tata Sampann", "Wingreens", "Sleepy Owl", "Farmley"],
    "Lifestyle": ["Philips", "Wipro", "Ikea", "Casio"],
    "Kids": ["Funskool", "Skillmatics", "Hamleys", "Faber-Castell"],
}


DELIVERY_BADGES = [
    "Free delivery by tomorrow",
    "Same-day delivery available",
    "Prime-speed delivery",
    "Open box delivery eligible",
    "Cashpoints bonus on checkout",
]


BUYER_NAMES = [
    "Maya Chen",
    "Jordan Patel",
    "Amelia Brooks",
    "Noah Williams",
    "Sophia Rivera",
    "Ethan Turner",
    "Ava Morgan",
    "Liam Harris",
    "Isabella Reed",
    "Lucas Bennett",
    "Mia Thompson",
    "Oliver Hayes",
    "Charlotte Kim",
    "Elijah Foster",
    "Harper Collins",
    "James Walker",
    "Evelyn Scott",
    "Benjamin Price",
    "Abigail Cooper",
    "Daniel Hughes",
]


SEGMENTS = ["VIP", "Frequent", "New", "Dormant", "Deal Seeker", "Family Shopper"]

LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

CONSENT_STATUSES = ["granted", "granted", "granted", "limited", "opted_out"]

POS_TERMINALS = [
    ("pos-001", "SwiftCart Jubilee Hills", "Hyderabad", "Register 01", "Aarav Reddy"),
    ("pos-002", "SwiftCart Gachibowli", "Hyderabad", "Register 02", "Neha Sharma"),
    ("pos-003", "SwiftCart Phoenix Mall", "Mumbai", "Express Counter", "Rohan Mehta"),
    ("pos-004", "SwiftCart Koramangala", "Bengaluru", "Register 03", "Isha Nair"),
    ("pos-005", "SwiftCart Velachery", "Chennai", "Self Checkout", "Kavya Rao"),
    ("pos-006", "SwiftCart FC Road", "Pune", "Register 01", "Aditya Kulkarni"),
]

POS_PAYMENT_METHODS = ["UPI", "Card", "Cash", "Wallet"]

CONNECTOR_FAMILIES = {
    "Beauty": "partner_catalog",
    "Electronics": "ecommerce_platform",
    "Grocery": "inventory_system",
    "Home": "partner_catalog",
    "Kids": "crm",
    "Lifestyle": "marketing_automation",
    "Outdoor": "inventory_system",
}


def seed_demo_data(db, max_discount_pct: int = 25) -> None:
    for collection in COLLECTIONS:
        db[collection].delete_many({})

    rng = random.Random(20260601)
    now = utcnow()

    sellers = []
    for seller_index, (seller_id, name, focus) in enumerate(SELLERS, start=1):
        connector_family = CONNECTOR_FAMILIES.get(focus, "ecommerce_platform")
        connector_health = rng.choices(["Healthy", "Healthy", "Healthy", "Degraded"], weights=[5, 3, 2, 1])[0]
        sellers.append(
            {
                "_id": seller_id,
                "seller_id": seller_id,
                "name": name,
                "category_focus": focus,
                "rating": round(rng.uniform(4.2, 4.9), 2),
                "revenue": 0.0,
                "active": True,
                "fulfillment_status": "Healthy",
                "fulfillment_rate": round(rng.uniform(92, 99), 1),
                "pending_orders": rng.randint(0, 4),
                "product_count": 0,
                "connector_id": f"conn-{seller_id}",
                "connector_family": connector_family,
                "connector_health": connector_health,
                "latency_ms": rng.randint(55, 430),
                "error_rate_pct": round(rng.uniform(0.1, 2.8 if connector_health == "Healthy" else 7.5), 2),
                "last_sync_status": "Synced" if connector_health == "Healthy" else "Retrying",
                "retry_queue_depth": 0 if connector_health == "Healthy" else rng.randint(2, 12),
                "supports_rollback": seller_index % 3 != 0,
                "decision_context": {
                    "connector_owner": "Marketplace Integrations",
                    "data_classification": "commercial_operations",
                    "allowed_actions": ["sync_catalog", "reserve_inventory", "create_order", "issue_refund"],
                    "policy_version": DECISION_POLICY_VERSION,
                },
                "updated_at": now,
            }
        )
    buyers = []
    for index, name in enumerate(BUYER_NAMES, start=1):
        buyer_id = f"buy-{index:03d}"
        first_name = name.split()[0].lower()
        segment = rng.choice(SEGMENTS)
        consent_status = "opted_out" if index in {4, 14} else rng.choice(CONSENT_STATUSES)
        loyalty_tier = LOYALTY_TIERS[min(len(LOYALTY_TIERS) - 1, index % len(LOYALTY_TIERS))]
        reward_cap_remaining = rng.randint(250, 2200)
        buyers.append(
            {
                "_id": buyer_id,
                "buyer_id": buyer_id,
                "name": name,
                "email": f"{first_name}.{index}@swiftcart.local",
                "segment": segment,
                "cashpoints_balance": rng.randint(75, 850),
                "risk_score": round(rng.uniform(0.05, 0.42), 2),
                "loyalty_tier": loyalty_tier,
                "consent_status": consent_status,
                "churn_risk": round(rng.uniform(0.08, 0.74), 2),
                "household_id": f"hh-{((index - 1) // 2) + 1:03d}",
                "device_fingerprint": f"dev-{buyer_id}-{rng.randint(1000, 9999)}",
                "frequency_cap_remaining": rng.randint(1, 8),
                "reward_cap_remaining": reward_cap_remaining,
                "quiet_hours": {"start": "22:00", "end": "08:00"},
                "segment_memberships": [segment, loyalty_tier, rng.choice(["high_margin_affinity", "price_sensitive", "replenishment"])],
                "decision_context": {
                    "customer_value_band": "high" if loyalty_tier in {"Gold", "Platinum"} else "standard",
                    "identity_confidence": round(rng.uniform(0.86, 0.99), 2),
                    "policy_version": DECISION_POLICY_VERSION,
                    "eligible_domains": ["loyalty", "promotions", "fraud", "transaction_governance"],
                },
                "lifetime_value": 0.0,
                "orders_count": 0,
                "abandoned_carts": rng.randint(0, 4),
                "status": rng.choices(["Active", "Active", "Active", "Dormant"], weights=[4, 3, 2, 1])[0],
                "last_active": now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 20)),
                "created_at": now - timedelta(days=rng.randint(10, 220)),
            }
        )

    products = []
    seller_product_counts = {seller_id: 0 for seller_id, _, _ in SELLERS}
    for index, (name, category, base_price, stock, seller_id) in enumerate(PRODUCTS, start=1):
        product_id = f"prd-{index:03d}"
        discount_pct = rng.choice([0, 0, 5, 8, 10, 12])
        discount_pct = min(discount_pct, max_discount_pct)
        price = round(max(1.0, base_price * (1 - discount_pct / 100)), 2)
        low_threshold = rng.randint(8, 16)
        gross_margin_pct = round(rng.uniform(0.18, 0.48), 3)
        margin_floor_pct = round(rng.uniform(0.14, 0.24), 3)
        partner_liability_pct = round(rng.uniform(0.15, 0.62), 2)
        seller_product_counts[seller_id] += 1
        products.append(
            {
                "_id": product_id,
                "product_id": product_id,
                "name": name,
                "slug": slugify(name),
                "category": category,
                "base_price": float(base_price),
                "price": price,
                "discount_pct": discount_pct,
                "stock": stock,
                "low_stock_threshold": low_threshold,
                "sold_count": rng.randint(8, 95),
                "views_count": rng.randint(80, 850),
                "carts_count": rng.randint(10, 130),
                "brand": rng.choice(PRODUCT_BRANDS.get(category, [category])),
                "rating": round(rng.uniform(4.0, 4.8), 1),
                "review_count": rng.randint(180, 9200),
                "delivery_badge": rng.choice(DELIVERY_BADGES),
                "promotion": rng.choice(["Bank offer", "Limited time deal", "Cashpoints extra"]) if discount_pct else "",
                "gross_margin_pct": gross_margin_pct,
                "margin_floor_pct": margin_floor_pct,
                "promotion_budget_remaining": rng.randint(45000, 225000),
                "discount_exposure_remaining": rng.randint(4000, 36000),
                "offer_eligible": stock > low_threshold and gross_margin_pct >= margin_floor_pct,
                "campaign_id": f"cmp-{category.lower()}-{rng.randint(101, 909)}",
                "partner_liability_pct": partner_liability_pct,
                "inventory_policy_status": "low_stock_block" if stock <= low_threshold else "eligible",
                "decision_context": {
                    "commercial_domain": "retail_catalog",
                    "policy_version": DECISION_POLICY_VERSION,
                    "margin_owner": "Category Finance",
                    "campaign_owner": "Growth Merchandising",
                    "evidence_fields": ["price", "stock", "discount_pct", "gross_margin_pct"],
                },
                "status": "Low Stock" if stock <= low_threshold else "Active",
                "seller_id": seller_id,
                "seller_status": "Active",
                "image_url": PRODUCT_IMAGES.get(name, CATEGORY_IMAGES.get(category, "/images/products/product.svg")),
                "created_at": now - timedelta(days=rng.randint(20, 180)),
                "updated_at": now,
            }
        )

    sellers_by_id = {seller["seller_id"]: seller for seller in sellers}
    for seller_id, count in seller_product_counts.items():
        sellers_by_id[seller_id]["product_count"] = count

    terminals = []
    for index, (terminal_id, store_name, city, register_name, cashier_name) in enumerate(POS_TERMINALS, start=1):
        status = rng.choices(["Open", "Open", "Busy", "Offline"], weights=[5, 3, 2, 1])[0]
        terminals.append(
            {
                "_id": terminal_id,
                "terminal_id": terminal_id,
                "store_name": store_name,
                "city": city,
                "register_name": register_name,
                "cashier_name": cashier_name,
                "status": status,
                "queue_depth": rng.randint(0, 7 if status != "Offline" else 0),
                "today_orders": 0,
                "today_revenue": 0.0,
                "total_orders": rng.randint(180, 820),
                "total_revenue": round(rng.uniform(320000, 1450000), 2),
                "average_ticket": 0.0,
                "cash_drawer_balance": round(rng.uniform(18000, 72000), 2),
                "payment_mix": {method: 0 for method in POS_PAYMENT_METHODS},
                "risk_alerts": rng.randint(0, 2),
                "returns_pending": rng.randint(0, 5),
                "last_sale_at": None,
                "decision_context": {
                    "commercial_domain": "store_checkout",
                    "policy_version": DECISION_POLICY_VERSION,
                    "allowed_actions": ["create_sale", "redeem_cashpoints", "issue_receipt", "flag_receipt"],
                    "evidence_fields": ["terminal_id", "payment_method", "queue_depth", "cash_drawer_balance"],
                },
                "updated_at": now,
            }
        )
    for terminal in terminals:
        terminal["average_ticket"] = round(
            float(terminal["total_revenue"]) / max(1, int(terminal["total_orders"])),
            2,
        )

    transactions = []
    ledger_entries = []
    products_by_id = {product["product_id"]: product for product in products}
    buyers_by_id = {buyer["buyer_id"]: buyer for buyer in buyers}
    terminals_by_id = {terminal["terminal_id"]: terminal for terminal in terminals}

    for index in range(1, 31):
        product = rng.choice(products)
        buyer = rng.choice(buyers)
        scenario = scenario_for_index(index)
        is_pos_sale = index % 3 == 0
        terminal = terminals[(index // 3 - 1) % len(terminals)] if is_pos_sale else None
        quantity = min(rng.randint(1, 3), max(1, product["stock"]))
        amount = round(product["price"] * quantity, 2)
        if scenario["key"] == "fraud_redemption_review":
            status = "Flagged"
        elif scenario["key"] in {"margin_floor_block", "consent_personalization_block", "inventory_low_stock_block"}:
            status = "Cancelled"
        elif scenario["key"] in {"approval_required_high_value", "connector_retry"}:
            status = "Pending"
        else:
            status = rng.choices(["Completed", "Pending"], weights=[9, 1])[0]
        inventory_applied = status in {"Completed", "Pending"}
        inventory_quantity = quantity if inventory_applied else 0
        if inventory_applied:
            product["stock"] = max(0, product["stock"] - quantity)
            product["sold_count"] += quantity
        if is_pos_sale:
            timestamp = now - timedelta(hours=rng.randint(0, 9), minutes=rng.randint(0, 59))
        else:
            timestamp = now - timedelta(days=rng.randint(0, 7), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        transaction_id = f"txn-seed-{index:03d}"
        decision_metadata = build_decision_metadata(
            source="seed",
            sequence=index,
            buyer=buyer,
            product=product,
            amount=amount,
            quantity=quantity,
            timestamp=timestamp,
            scenario_key=scenario["key"],
            suspicious=status == "Flagged",
            status=status,
        )
        if is_pos_sale:
            decision_metadata["event_type"] = "pos.checkout"
            decision_metadata["channel"] = "store_pos"
        payment_method = rng.choice(POS_PAYMENT_METHODS) if is_pos_sale else rng.choice(["UPI", "Card", "Net Banking", "Wallet"])
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
            "status": status,
            "suspicious": status == "Flagged",
            "risk_score": buyer["risk_score"],
            "inventory_applied": True,
            "inventory_quantity_applied": inventory_quantity,
            "points_applied": status == "Completed",
            "sales_channel": "Point of Sale" if is_pos_sale else "Marketplace",
            "payment_method": payment_method,
            "timestamp": timestamp,
            **decision_metadata,
        }
        if terminal:
            transaction.update(
                {
                    "pos_terminal_id": terminal["terminal_id"],
                    "store_name": terminal["store_name"],
                    "store_city": terminal["city"],
                    "register_name": terminal["register_name"],
                    "cashier_name": terminal["cashier_name"],
                    "receipt_id": f"rcpt-{terminal['terminal_id']}-{index:04d}",
                }
            )
        transactions.append(transaction)

        if status in {"Completed", "Pending"}:
            buyer["orders_count"] += 1
            buyer["lifetime_value"] = round(buyer["lifetime_value"] + amount, 2)
        buyer["last_active"] = max(buyer["last_active"], timestamp)
        if status in {"Completed", "Pending"}:
            sellers_by_id[product["seller_id"]]["revenue"] = round(
                sellers_by_id[product["seller_id"]]["revenue"] + amount, 2
            )
        if status == "Pending":
            sellers_by_id[product["seller_id"]]["pending_orders"] += 1

        if terminal and status in {"Completed", "Pending"}:
            pos_terminal = terminals_by_id[terminal["terminal_id"]]
            pos_terminal["today_orders"] += 1
            pos_terminal["today_revenue"] = round(pos_terminal["today_revenue"] + amount, 2)
            pos_terminal["total_orders"] += 1
            pos_terminal["total_revenue"] = round(pos_terminal["total_revenue"] + amount, 2)
            pos_terminal["average_ticket"] = round(
                pos_terminal["total_revenue"] / max(1, pos_terminal["total_orders"]),
                2,
            )
            pos_terminal["payment_mix"][payment_method] += 1
            if payment_method == "Cash":
                pos_terminal["cash_drawer_balance"] = round(pos_terminal["cash_drawer_balance"] + amount, 2)
            pos_terminal["queue_depth"] = rng.randint(0, 8)
            pos_terminal["status"] = "Busy" if pos_terminal["queue_depth"] >= 5 else "Open"
            pos_terminal["last_sale_at"] = timestamp
            pos_terminal["updated_at"] = timestamp

        if status == "Completed":
            points = max(1, int(amount * 0.05))
            buyer["cashpoints_balance"] += points
            ledger_metadata = build_ledger_metadata(
                source="seed",
                sequence=index,
                buyer=buyer,
                points=points,
                timestamp=timestamp,
                scenario_key=scenario["key"],
                suspicious=False,
            )
            ledger_entries.append(
                {
                    "_id": f"cp-seed-{index:03d}",
                    "ledger_id": f"cp-seed-{index:03d}",
                    "buyer_id": buyer["buyer_id"],
                    "buyer_name": buyer["name"],
                    "transaction_id": transaction_id,
                    "points": points,
                    "balance_after": buyer["cashpoints_balance"],
                    "entry_type": "Earned",
                    "reason": "Seed purchase reward",
                    "suspicious": False,
                    "timestamp": timestamp,
                    **ledger_metadata,
                }
            )

        if status == "Flagged":
            flagged_points = max(1, int(amount * 0.08))
            ledger_metadata = build_ledger_metadata(
                source="seed",
                sequence=f"flag-{index}",
                buyer=buyer,
                points=-flagged_points,
                timestamp=timestamp,
                scenario_key=scenario["key"],
                suspicious=True,
            )
            ledger_entries.append(
                {
                    "_id": f"cp-flag-seed-{index:03d}",
                    "ledger_id": f"cp-flag-seed-{index:03d}",
                    "buyer_id": buyer["buyer_id"],
                    "buyer_name": buyer["name"],
                    "transaction_id": transaction_id,
                    "points": -min(buyer["cashpoints_balance"], flagged_points),
                    "balance_after": max(0, buyer["cashpoints_balance"] - flagged_points),
                    "entry_type": "Flagged Redemption",
                    "reason": "Seeded high-risk loyalty redemption review",
                    "suspicious": True,
                    "timestamp": timestamp,
                    **ledger_metadata,
                }
            )

    for product in products_by_id.values():
        product["status"] = "Low Stock" if product["stock"] <= product["low_stock_threshold"] else "Active"
        product["inventory_policy_status"] = "low_stock_block" if product["status"] == "Low Stock" else "eligible"
        product["offer_eligible"] = product["status"] == "Active" and product["gross_margin_pct"] >= product["margin_floor_pct"]

    for seller in sellers:
        if seller["pending_orders"] > 7:
            seller["fulfillment_status"] = "At Risk"
        elif seller["pending_orders"] > 3:
            seller["fulfillment_status"] = "Busy"

    db["sellers"].insert_many(sellers)
    db["buyers"].insert_many(list(buyers_by_id.values()))
    db["products"].insert_many(list(products_by_id.values()))
    db["pos_terminals"].insert_many(list(terminals_by_id.values()))
    db["transactions"].insert_many(transactions)
    if ledger_entries:
        db["cashpoints_ledger"].insert_many(ledger_entries)

    db["simulation_config"].insert_one(
        {
            "_id": "main",
            "running": True,
            "speed": "five_minute",
            "interval_seconds": 300,
            "max_discount_pct": max_discount_pct,
            "dataset_version": DATASET_VERSION,
            "tick_count": 0,
            "decision_policy_version": DECISION_POLICY_VERSION,
            "decision_test_matrix": DECISION_TEST_CASE_KEYS,
            "updated_at": now,
        }
    )

    db["agent_activity_log"].insert_one(
        {
            "_id": "log-seed-001",
            "agent_name": "Seed Agent",
            "action_type": "seed",
            "affected_collection": "all",
            "affected_id": "swiftcart",
            "old_value": {},
            "new_value": {
                "products": len(products),
                "buyers": len(buyers),
                "sellers": len(sellers),
                "transactions": len(transactions),
                "pos_terminals": len(terminals),
            },
            "reason": "Marketplace and point-of-sale collections initialized with deterministic ecommerce data.",
            "validation_status": "passed",
            "policy_version": DECISION_POLICY_VERSION,
            "decision_test_case": "seed_dataset",
            "autonomy_level": "Level 3 - Bounded Autonomy",
            "evidence_refs": [{"type": "seed_fixture", "ref": "swiftcart_marketplace"}],
            "timestamp": now,
        }
    )

    recalculate_and_store_metrics(db)
