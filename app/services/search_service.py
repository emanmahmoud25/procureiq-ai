"""
Search service
──────────────
Runs Tavily queries and builds Product objects.
Price strategy (delegated to TavilyClient):
  1. extract() on product URL       ← real page price
  2. SERP snippet on same site      ← Google Shopping price
  3. SERP snippet on alt site       ← fallback
"""

import re
import logging
from typing import Optional

from app.clients.tavily_client import TavilyClient
from app.models.schemas import SearchResult, Product
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

_JUNK_TITLES = {
    "sorry, there was a problem.", "delivering to", "sign in",
    "just a moment", "error", "access denied", "robot check", "captcha",
}


_HARD_JUNK = [
    "/s?k=", "/b?ie=", "/s?i=", "node=", "/gp/bestsellers", "/gp/",
    "/search", "?cat=",
    "/c/", "/brand/",
]


def is_junk_title(title: str) -> bool:
    t = title.lower().strip()
    return any(j in t for j in _JUNK_TITLES) or len(t) < 8


def clean_search_title(raw: str) -> str:
    cleaned = re.sub(r'^Buy\s+', '', raw, flags=re.IGNORECASE)
    cleaned = re.sub(
        r'\s*[-–|]\s*(Souq is now|Best Prices? in|Buy @|Online|Egypt[-\s]'
        r'|Jumia|Amazon|Noon|Carrefour|Extra).*$',
        '', cleaned, flags=re.IGNORECASE,
    ).strip().rstrip(".,- ")
    return cleaned[:100] if cleaned else raw[:100]

def get_source(url: str) -> str:
    if "amazon.eg"          in url: return "Amazon.eg"
    if "jumia.com.eg"       in url: return "Jumia.eg"
    if "noon.com"           in url: return "Noon.eg"
    if "carrefouregypt.com" in url: return "Carrefour Egypt"
    if "extra.com.eg"       in url: return "Extra Egypt"
    return "Other"


def build_product_name(search_title: str, url: str) -> str:
    if search_title and not is_junk_title(search_title):
        return clean_search_title(search_title)
    parts = url.rstrip("/").split("/")
    for part in reversed(parts):
        if len(part) > 10 and not part.startswith("dp") and not part.startswith("B0"):
            return part.replace("-", " ").replace("_", " ").title()[:80]
    return "product"


def _is_product_url(url: str) -> bool:
    # ── Hard junk patterns ─────────────────────────────────
    if any(p in url for p in _HARD_JUNK):
        return False

    # ── Amazon ─────────────────────────────────────────────
    if "amazon.eg" in url:
        logger.info(f"🔗 Full URL: {url}")
        return "/dp/" in url

    # ── Jumia ──────────────────────────────────────────────
    if "jumia.com.eg" in url:
        path = url.split("jumia.com.eg")[-1].split("?")[0].strip("/")
        segments = [s for s in path.split("/") if s]

        # category أو brand: segment واحد أو اتنين بدون أرقام
        if len(segments) <= 2 and not re.search(r'\d', path):
            return False

        # product: segment واحد فيه dash وطويل (اسم المنتج)
        if len(segments) == 1 and "-" in path and len(path) > 15:
            return True

        return False

    # ── Noon ───────────────────────────────────────────────
    if "noon.com" in url:
        path = url.split("egypt-en/")[-1].split("?")[0].strip("/")
        segments = [s for s in path.split("/") if s]
        if segments and "-" in segments[0] and len(segments[0]) > 10:
            return True
        return False

    # ── Carrefour ──────────────────────────────────────────
    if "carrefouregypt.com" in url:
        if re.search(r'/en/c/', url):
            return False
        if "/p/" in url:
            return True
        path = url.split("mafegy/en/")[-1].split("?")[0].strip("/")
        segments = [s for s in path.split("/") if s]
        if len(segments) >= 2 and "-" in segments[-1] and len(segments[-1]) > 10:
            return True
        return False

    # ── Extra ──────────────────────────────────────────────
    if "extra.com.eg" in url:
        path = url.rstrip("/").split("/")[-1]
        return len(path) > 10 and "-" in path

    return False


class SearchService:
    def __init__(self):
        self.client = TavilyClient()

    def _build_queries(self, product_name: str) -> list[str]:
        queries = []

        # Sites الأساسية
        primary_sites = [
            "amazon.eg",
            "jumia.com.eg",
            "noon.com/egypt-en",
        ]
        for site in primary_sites:
            queries.append(f"{product_name} site:{site}")
            queries.append(f"buy {product_name} Egypt site:{site}")
            queries.append(f"{product_name} price EGP site:{site}")

        # Fallback sites
        fallback_sites = [
            "carrefouregypt.com",
            "extra.com.eg",
        ]
        for site in fallback_sites:
            queries.append(f"{product_name} site:{site}")
            queries.append(f"{product_name} price EGP site:{site}")

        return queries

    def run_searches(self, product_name: str, score_threshold: float = None) -> list[SearchResult]:
        queries = self._build_queries(product_name)
        threshold = score_threshold or settings.score_threshold
        results: list[SearchResult] = []
        seen: set[str] = set()

        for q in queries:
            logger.info(f"🔍 {q}")
            raw = self.client.search(q, max_results=settings.max_results_per_query)
            for r in raw.get("results", []):
                url = r.get("url", "")
                if r.get("score", 0) >= threshold and url not in seen:
                    seen.add(url)
                    results.append(SearchResult(
                        url=url,
                        title=r.get("title", "")[:120],
                        score=round(r.get("score", 0), 3),
                        search_query=q,
                        content=r.get("content", "")[:300],
                    ))
        return results

    def build_product(self, r: SearchResult) -> Product:
        url       = r.url
        raw_title = r.title
        content   = r.content

        if not _is_product_url(url):
            logger.info(f"⏭ Skipping non-product URL: {url[:70]}")
            return _empty_product(url)

        title = clean_search_title(raw_title) if not is_junk_title(raw_title) else "Product"

        lines = [
            l.strip() for l in content.split(".")
            if l.strip() and len(l.strip()) > 20
            and "Fashion" not in l and "cookie" not in l.lower()
        ]
        description = ". ".join(lines[:2])[:250] or ""

        price = self.client.extract_price(content + " " + raw_title)
        if not price:
            logger.info(f"💰 Fetching price for: {title[:45]}")
            price = self.client.fetch_price(title, url)

        logger.info(f"🖼  Fetching image for: {title[:45]}")
        image_url = self.client.fetch_image(title, url) or ""

        price_num: Optional[float] = None
        try:
            if price and price != "N/A":
                price_num = float(price)
        except ValueError:
            pass

        logger.info(
            f"✅ Built: {title[:40]} | "
            f"Price: EGP {price} | "
            f"Image: {'✓' if image_url else '✗'} | "
            f"Source: {get_source(url)}"
        )

        return Product(
            page_url=url,
            product_url=url,
            product_title=title,
            product_image_url=image_url,
            product_current_price=price or "N/A",
            price_numeric=price_num,
            description=description,
            source_title=raw_title,
        )


def _empty_product(url: str) -> Product:
    return Product(
        page_url=url,
        product_url=url,
        product_title="N/A",
        product_current_price="N/A",
    )