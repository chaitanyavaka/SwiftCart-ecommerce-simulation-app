from __future__ import annotations

from html import escape

from flask import Blueprint, Response, current_app


assets_bp = Blueprint("assets", __name__)


CATEGORY_STYLES = {
    "Electronics": ("#233142", "#2fd1c5", "#f6f8fb"),
    "Home": ("#2f3a32", "#9ad17b", "#fff8eb"),
    "Outdoor": ("#203a43", "#ffb347", "#f5fbff"),
    "Beauty": ("#3f263f", "#ff8fb3", "#fff5f8"),
    "Grocery": ("#33412e", "#ffd166", "#f8fff1"),
    "Lifestyle": ("#2d3142", "#7bdff2", "#f6f5ff"),
    "Kids": ("#31324a", "#f7a072", "#fffaf0"),
}


@assets_bp.route("/images/products/<slug>.svg")
def product_image(slug: str):
    db = current_app.extensions["demo_db"]
    product = db["products"].find_one({"slug": slug}) or {}
    name = product.get("name", slug.replace("-", " ").title())
    category = product.get("category", "Product")
    primary, accent, background = CATEGORY_STYLES.get(category, ("#2d3142", "#52b788", "#f6f8fb"))
    short_name = " ".join(name.split()[:3])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="520" viewBox="0 0 720 520" role="img" aria-label="{escape(name)}">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="{background}"/>
      <stop offset="1" stop-color="#ffffff"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#111827" flood-opacity="0.16"/>
    </filter>
  </defs>
  <rect width="720" height="520" rx="36" fill="url(#bg)"/>
  <circle cx="600" cy="95" r="62" fill="{accent}" opacity="0.22"/>
  <circle cx="116" cy="416" r="88" fill="{primary}" opacity="0.08"/>
  <g filter="url(#shadow)">
    <rect x="170" y="112" width="380" height="250" rx="30" fill="#ffffff"/>
    <rect x="214" y="154" width="292" height="130" rx="26" fill="{primary}" opacity="0.92"/>
    <rect x="248" y="303" width="224" height="20" rx="10" fill="{accent}"/>
    <circle cx="260" cy="219" r="35" fill="{accent}" opacity="0.92"/>
    <rect x="322" y="194" width="130" height="18" rx="9" fill="#ffffff" opacity="0.86"/>
    <rect x="322" y="230" width="88" height="16" rx="8" fill="#ffffff" opacity="0.58"/>
  </g>
  <text x="52" y="72" fill="{primary}" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700">{escape(category)}</text>
  <text x="52" y="452" fill="{primary}" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="800">{escape(short_name)}</text>
  <text x="52" y="486" fill="#5b6472" font-family="Inter, Arial, sans-serif" font-size="20">SwiftCart product image</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")
