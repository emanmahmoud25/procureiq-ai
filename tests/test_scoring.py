"""
Unit tests for scoring service — no API calls needed.
"""
import pytest
from app.models.schemas import Product, SearchResult
from app.services.scoring_service import score_products


def make_product(price, title="Standing Desk", url="https://amazon.eg/p1"):
    return Product(
        page_url=url,
        product_url=url,
        product_title=title,
        product_current_price=str(price) if price else "N/A",
        price_numeric=float(price) if price else None,
        description="A great ergonomic standing desk with adjustable height.",
        product_image_url="https://example.com/img.jpg",
    )


def make_result(url, score=0.8):
    return SearchResult(url=url, title="test", score=score, search_query="test", content="")


def test_exact_target_gets_max_proximity():
    products = [make_product(5000)]
    results = [make_result("https://amazon.eg/p1")]
    ranked = score_products(products, results, target_price=5000)
    assert ranked[0].score_breakdown.price_proximity == 25


def test_product_outside_tolerance_gets_zero_proximity():
    products = [make_product(10000)]
    results = [make_result("https://amazon.eg/p1")]
    ranked = score_products(products, results, target_price=5000, price_tolerance_pct=30)
    assert ranked[0].score_breakdown.price_proximity == 0


def test_ranking_prefers_closest_to_target():
    p1 = make_product(5200, url="https://amazon.eg/p1")   # close to 5000
    p2 = make_product(9500, url="https://jumia.com.eg/p2")  # far from 5000
    results = [make_result("https://amazon.eg/p1"), make_result("https://jumia.com.eg/p2")]
    ranked = score_products([p1, p2], results, target_price=5000)
    assert ranked[0].page_url == "https://amazon.eg/p1"


def test_no_price_gets_zero_price_scores():
    products = [make_product(None)]
    results = [make_result("https://amazon.eg/p1")]
    ranked = score_products(products, results, target_price=5000)
    bd = ranked[0].score_breakdown
    assert bd.price_available == 0
    assert bd.price_competitiveness == 0
    assert bd.price_proximity == 0


def test_diff_pct_sign():
    products = [make_product(6000)]
    results = [make_result("https://amazon.eg/p1")]
    ranked = score_products(products, results, target_price=5000)
    # 6000 is 20% above 5000
    assert ranked[0].price_diff_pct == pytest.approx(20.0, 0.1)
