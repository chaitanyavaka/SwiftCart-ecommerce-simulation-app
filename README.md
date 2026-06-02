# SwiftCart Marketplace

A standalone Flask + MongoDB ecommerce simulation with a customer-facing marketplace UI and an automated agent layer. The app looks like a live shopping site while background agents continuously update products, buyers, sellers, loyalty points, transactions and risk signals.

## What Is Included

- Admin login/logout
- Amazon/Flipkart-style marketplace header, search bar, category nav, hero sale area and product cards
- Products, buyers, sellers, cashpoints, transactions and agent activity pages
- Real product-style image URLs for seeded products
- Background agents for buyer activity, inventory, sellers, cashpoints, promotions, anomaly detection and metrics
- Fixed 5-minute agent refresh cadence
- MongoDB persistence through `MONGO_URI`
- Optional Groq explanations through `GROQ_API_KEY`
- In-memory fallback for local tests or offline previews
- Commerce decision fixtures in the existing APIs for policy, decision, audit, loyalty, fraud and connector testing

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `py` is not available, use your installed Python executable directly.

## Environment

Create a local `.env` or set variables in PowerShell. Do not commit real secrets.

```powershell
$env:SECRET_KEY="replace-me"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="demo123"
$env:MONGO_URI="mongodb+srv://USER:PASSWORD@cluster.example.mongodb.net/"
$env:MONGO_DB_NAME="swiftcart_marketplace"
$env:GROQ_API_KEY="your_groq_key"
$env:AGENT_INTERVAL_SECONDS="300"
$env:AUTO_START_SIMULATION="true"
```

The Atlas URI must include your real username, password, and cluster host. If `pymongo` is not installed or MongoDB is unreachable, the app can fall back to the in-memory backend when `MONGO_FALLBACK_TO_MEMORY=true`.

## Run

```powershell
python seed_demo.py
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and log in with `admin` / `demo123` unless you changed the credentials.

To run on a different port:

```powershell
python run.py --port 5010
```

## Agent Timing

Agents run every 5 minutes by default:

```powershell
$env:AGENT_INTERVAL_SECONDS="300"
```

The storefront does not show manual automation controls. Agents auto-start when the server starts if `AUTO_START_SIMULATION=true`.

## Existing JSON APIs

- `GET /api/products`
- `GET /api/buyers`
- `GET /api/sellers`
- `GET /api/transactions`
- `GET /api/cashpoints`
- `GET /api/metrics`
- `GET /api/agent-activity`
- `POST /api/admin/simulation/start`
- `POST /api/admin/simulation/stop`
- `POST /api/admin/simulation/reset`
- `POST /api/admin/simulation/speed`

Admin API endpoints require login.

## Decision Test Data

SwiftCart stays visually ecommerce, but the records returned by the existing endpoints include commerce decision test artifacts:

- transactions include `decision_id`, `request_id`, `idempotency_key`, `policy_checks`, `decision_context_pack`, `action_graph`, `execution_receipt`, approval status, autonomy level, rollback flags, fraud signals, experiment holdout data and expected margin impact
- products include margin floors, promotion budgets, offer eligibility, inventory policy status and pricing policy decisions
- buyers include consent status, loyalty tier, churn risk, household/device identity and customer value context
- sellers include connector IDs, connector family, health, latency, retry depth and rollback support
- cashpoints ledger entries include wallet policy results, liability owner, redemption velocity and linked decision metadata
- metrics include covered decision test cases, policy blocks, approval queue count, connector retries and decision audit record count

The seeded transaction set covers the current decision scenarios: loyalty reward allowed, fraud redemption review, margin floor block, consent personalization block, inventory low-stock block, high-value approval required, connector retry, holdout experiment, rollback-ready execution and deterministic fallback.

## Tests

```powershell
python -m unittest discover
```

The tests cover app startup, seed data, decision fixture coverage, unchanged API surface, inventory and cashpoints safety, discount limits, transaction generation, agent logging, and reset behavior.
