"""
Scoring service — scores and ranks products.
KEY ADDITION: price_proximity score — rewards products close to the target price.
"""
import math
from app.models.schemas import Product, ScoreBreakdown, SearchResult
from app.services.search_service import is_junk_title


def score_products(products: list[Product],search_results: list[SearchResult],target_price: float,price_tolerance_pct: float = 30.0,
) -> list[Product]:
    """
    Score and rank all products based on multiple weighted criteria.

    Inputs:
    - products: list of Product objects to evaluate
    - search_results: original search results used to get search relevance scores
    - target_price: the budget / target price entered by the user
    - price_tolerance_pct: allowed percentage distance from target price before score drops to 0

    Returns:
    - list of Product objects sorted by highest score first
    """

    # Create a mapping between each result URL and its Tavily search relevance score
    # Example:
    # {
    #   "https://amazon.eg/item1": 0.91,
    #   "https://jumia.com.eg/item2": 0.84
    # }
    url_to_score = {r.url: r.score for r in search_results}

    # Extract all numeric prices from the products
    prices = [p.price_numeric for p in products]

    # Keep only valid numeric prices (ignore None)
    valid = [x for x in prices if x is not None]

    # Get min and max price across all products
    # Used later to compare how competitive each price is
    min_p = min(valid) if valid else 0
    max_p = max(valid) if valid else 1

    # This list will store all scored products
    scored = []

    # Loop through each product and calculate its score
    for i, p in enumerate(products):
        # Create a new score breakdown object for this product
        # This stores the score of each individual criterion
        bd = ScoreBreakdown()

        # Final total score for this product
        score = 0

        # Current product numeric price
        pv = prices[i]

        # ① Price available (25 pts)
        # Give full points if the product has a price
        # Otherwise give 0
        bd.price_available = 25 if pv is not None else 0
        score += bd.price_available

        # ② Price competitiveness vs other results (25 pts)
        # Reward cheaper products compared to the rest of the list
        # Cheapest product gets highest score, most expensive gets lowest
        if pv is not None and max_p != min_p:
            bd.price_competitiveness = int(25 * (1 - (pv - min_p) / (max_p - min_p)))
        elif pv is not None:
            # If all products have the same price, give a neutral middle score
            bd.price_competitiveness = 12
        score += bd.price_competitiveness

        # ③ Price proximity to TARGET (25 pts) — KEY NEW CRITERION
        # Reward products that are close to the user's target price
        if pv is not None and target_price > 0:
            # Calculate absolute difference from target as a percentage
            diff_pct = abs(pv - target_price) / target_price * 100

            # Save signed difference percentage on the product itself
            # Positive = above target, Negative = below target
            p.price_diff_pct = round((pv - target_price) / target_price * 100, 1)

            # Full points if price is within 5% of target
            if diff_pct <= 5:
                bd.price_proximity = 25

            # Partial score if still within allowed tolerance
            elif diff_pct <= price_tolerance_pct:
                bd.price_proximity = int(25 * (1 - diff_pct / price_tolerance_pct))

            # No points if too far from target
            else:
                bd.price_proximity = 0
        score += bd.price_proximity

        # ④ Description quality (10 pts)
        # Reward products with better / longer descriptions
        desc = p.description or ""
        bd.description_quality = 10 if len(desc) > 40 else (5 if len(desc) > 10 else 0)
        score += bd.description_quality

        # ⑤ Has image (8 pts)
        # Give points if the product has an image
        bd.has_image = 8 if p.product_image_url else 0
        score += bd.has_image

        # ⑥ Clear title (4 pts)
        # Reward products with a meaningful, non-junk title
        t = p.product_title or ""
        bd.clear_title = 4 if (t and not is_junk_title(t) and len(t) > 10) else 0
        score += bd.clear_title

        # ⑦ Search relevance (13 pts)
        # Use the original Tavily search score to reward more relevant results
        rel = url_to_score.get(p.page_url, 0)
        bd.search_relevance = int(rel * 13)
        score += bd.search_relevance

        # Save final score and breakdown inside the product object
        p.score = score
        p.score_breakdown = bd

        # Add scored product to the list
        scored.append(p)

    # Sort all products by total score in descending order
    # Highest score = best product first
    scored.sort(key=lambda x: x.score, reverse=True)

    # Assign rank numbers after sorting
    # 1 = best product, 2 = second best, etc.
    for rank, item in enumerate(scored, 1):
        item.rank = rank

    # Return the ranked list
    return scored