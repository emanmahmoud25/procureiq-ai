"""
Tavily API client
─────────────────
Price extraction strategy (in order):

1. extract()  → scrape the actual product page directly
               Best for Jumia & Noon (static HTML)
               Amazon: JS-rendered → usually falls to step 2

2. SERP()     → Google Shopping snippet on the SAME site only
               "product name price EGP site:amazon.eg"

NO alt-site fallback — a price from a different site is wrong.
If no price found on the original site → return "N/A"
"""

import re
import time
import logging
from typing import Optional
from tavily import TavilyClient as _Tavily
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

# ── Price regex — priority order ──────────────────────────────────────────────
_PRICE_PRIORITY = [
    r'EGP\s*([\d][0-9,\.]+)',
    r'ج\.م\s*([\d][0-9,\.]+)',
    r'£E\s*([\d][0-9,\.]+)',
    r'Price[:\s]+EGP\s*([\d][0-9,\.]+)',
]
_PRICE_FALLBACK = [
    r'([\d][0-9,\.]+)\s*EGP',
    r'(?:price|Price|PRICE)[^\d]*([\d]{3,6})',
]

# ── Realistic price ceiling per category (EGP) ────────────────────────────────
_MAX_PRICE = 50_000   # above this → likely a wrong number (e.g. 164,347)
_MIN_PRICE = 50       # below this → likely not a price

# ── Image junk filters ────────────────────────────────────────────────────────
_IMG_JUNK = re.compile(
    r'(?:logo|icon|sprite|pixel|tracking|banner|ad[_-]|favicon|'
    r'placeholder|blank|loading|spinner|arrow|btn|button|nav[-_])',
    re.IGNORECASE,
)
_IMG_SMALL = re.compile(r'[-_](\d{1,2})x(\d{1,2})[-_.]')

# ── Alt sites for IMAGE only (not price) ─────────────────────────────────────
_ALT_SITES_IMAGE = {
    "amazon.eg":          ["jumia.com.eg", "noon.com"],
    "jumia.com.eg":       ["amazon.eg",    "noon.com"],
    "noon.com":           ["amazon.eg",    "jumia.com.eg"],
    "carrefouregypt.com": ["amazon.eg",    "jumia.com.eg"],
    "extra.com.eg":       ["amazon.eg",    "jumia.com.eg"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_price(text: str) -> Optional[str]:
    """
    Extract first valid EGP price from text.
    Valid range: 50 – 50,000 EGP.
    Priority: patterns with explicit EGP symbol first.
    """
    for pat in _PRICE_PRIORITY:
        for m in re.finditer(pat, text, re.IGNORECASE):
            raw = m.group(1).replace(",", "").replace(" ", "").split(".")[0]
            try:
                val = int(raw)
                if _MIN_PRICE <= val <= _MAX_PRICE:
                    return str(val)
            except ValueError:
                pass

    for pat in _PRICE_FALLBACK:
        for m in re.finditer(pat, text, re.IGNORECASE):
            raw = m.group(1).replace(",", "").replace(" ", "").split(".")[0]
            try:
                val = int(raw)
                if _MIN_PRICE <= val <= _MAX_PRICE:
                    return str(val)
            except ValueError:
                pass

    return None


def _is_good_image(url: str) -> bool:
    if not url or len(url) < 20:        return False
    if _IMG_JUNK.search(url):           return False
    if _IMG_SMALL.search(url):          return False
    if "1x1" in url or "blank" in url:  return False
    if not re.search(r'\.(jpg|jpeg|png|webp)(\?|$)', url, re.IGNORECASE):
        return False
    return True


def _get_source(url: str) -> str:
    if "amazon.eg"          in url: return "amazon.eg"
    if "jumia.com.eg"       in url: return "jumia.com.eg"
    if "noon.com"           in url: return "noon.com"
    if "carrefouregypt.com" in url: return "carrefouregypt.com"
    if "extra.com.eg"       in url: return "extra.com.eg"
    return ""


def _is_product_url(url: str) -> bool:
    junk = ["/s?k=", "/b?ie=", "/s?i=", "node=", "/search",
            "/c/", "?cat=", "category"]
    return not any(p in url for p in junk)


def _asin(url: str) -> Optional[str]:
    m = re.search(r'/dp/([A-Z0-9]{10})', url)
    return m.group(1) if m else None


# ══════════════════════════════════════════════════════════════════════════════
class TavilyClient:

    def __init__(self):
        self._tv = _Tavily(api_key=settings.tavily_api_key)

    # ── search ────────────────────────────────────────────────────────────────
    def search(self, query: str, max_results: int = 5,
               include_images: bool = False) -> dict:
        time.sleep(settings.search_delay)
        try:
            return self._tv.search(query=query, max_results=max_results,
                                   include_images=include_images)
        except Exception as e:
            logger.warning(f"Search error '{query[:50]}': {e}")
            return {"results": [], "images": []}

    # ── fetch_price ───────────────────────────────────────────────────────────
    def fetch_price(self, product_name: str, source_url: str) -> str:
        source = _get_source(source_url)

        # Step 1 — direct page scrape
        price = self._price_from_extract(source_url)
        if price:
            logger.info(f"✅ Price from extract(): EGP {price} | {source_url[:55]}")
            return price

        # Step 2 — SERP on same site only
        if source:
            price = self._price_from_serp(product_name, source)
            if price:
                logger.info(f"✅ Price from SERP ({source}): EGP {price}")
                return price

        logger.warning(f"❌ No price found for: {product_name[:50]}")
        return "N/A"

    # ── fetch_image ───────────────────────────────────────────────────────────
    def fetch_image(self, product_name: str, source_url: str) -> str:
        """
        Try original site first, then alt sites for image only.
        Image from a different site is still a valid product image.
        """
        source      = _get_source(source_url)
        source_asin = _asin(source_url)
        sites       = [source] + _ALT_SITES_IMAGE.get(source, [])

        for site in sites:
            if not site:
                continue
            for q in [
                f'"{product_name[:55]}" site:{site}',
                f'{product_name[:55]} product image site:{site}',
            ]:
                try:
                    time.sleep(settings.image_search_delay)
                    raw = self._tv.search(query=q, max_results=5,
                                          include_images=True)

                    for r in raw.get("results", []):
                        rurl = r.get("url", "")
                        if site not in rurl:
                            continue
                        if not _is_product_url(rurl):
                            continue
                        if site == "amazon.eg":
                            if "/dp/" not in rurl:
                                continue
                            if source_asin and _asin(rurl) != source_asin:
                                continue
                        img = r.get("image", "") or ""
                        if _is_good_image(img):
                            logger.info(f"🖼 Image from result.image ({site})")
                            return img

                    for img in raw.get("images", []):
                        img_url = img if isinstance(img, str) else img.get("url", "")
                        if _is_good_image(img_url):
                            logger.info(f"🖼 Image from SERP images ({site})")
                            return img_url

                except Exception as e:
                    logger.warning(f"Image search error ({site}): {e}")

        return ""

    # ── extract_price (public — used by search_service for snippet) ───────────
    def extract_price(self, text: str) -> Optional[str]:
        return _parse_price(text)

    # ── PRIVATE ───────────────────────────────────────────────────────────────
    def _price_from_extract(self, url: str) -> Optional[str]:
        """Scrape the product page with Tavily extract()."""
        try:
            time.sleep(settings.price_search_delay)          
            result = self._tv.extract(urls=[url])
            for r in result.get("results", []):
                content = r.get("raw_content", "") or ""
                if not content:
                    logger.warning(f"extract() empty content: {url[:55]}")
                    continue
                price = _parse_price(content[:5000])  
                if price:
                    return price
                logger.warning(
                    f"extract() has content but no valid price "
                    f"(JS-rendered?): {url[:55]}"
                )
        except Exception as e:
            logger.warning(f"extract() failed: {url[:55]}: {e}")
        return None

    def _price_from_serp(self, product_name: str, site: str) -> Optional[str]:
        """Search Google SERP for the product price on a specific site."""
        short   = product_name[:55]
        queries = [
            f'"{short}" price EGP site:{site}',
            f'"{short}" EGP site:{site}',
        ]
        for q in queries:
            try:
                time.sleep(settings.price_search_delay)      # ← price_search_delay (not price_search_delay)
                raw = self._tv.search(query=q, max_results=5)
                for r in raw.get("results", []):
                    rurl    = r.get("url",     "") or ""
                    title   = r.get("title",   "") or ""
                    content = r.get("content", "") or ""

                    if site not in rurl:                              continue
                    if not _is_product_url(rurl):                     continue
                    if site == "amazon.eg" and "/dp/" not in rurl:    continue

                    price = _parse_price(title + " " + content)
                    if price:
                        return price
            except Exception as e:
                logger.warning(f"SERP price error ({site}): {e}")
        return None