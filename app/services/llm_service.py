"""
LLM service — uses Groq to generate:
  1. introduction paragraph  (summary of the search)
  2. recommendation paragraph (why the top product was chosen)
  3. search queries for price extraction (optional, can be hardcoded)

Falls back to templated text if Groq is unavailable / key not set.
"""
import logging
import time
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _groq_call(prompt: str, max_tokens: int = 300) -> Optional[str]:
    """Raw Groq completion — returns text or None on failure."""
    if not settings.groq_api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=settings.temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq call failed: {e}")
        return None


# ── public functions ───────────────────────────────────────────────────────────
# 1- introduction paragraph
def generate_introduction(product_name: str,company: str,target_price: float,total_found: int
                          ,platforms: list[str],) -> str:
    """
    Returns a 2-3 sentence intro paragraph for the procurement report.
    Saved as step_5_introduction.json
    """
    platforms_str = ", ".join(platforms) if platforms else "major Egyptian e-commerce platforms"

    prompt = (
        f"You are a senior procurement analyst at {company}. "
        f"Write exactly 2-3 sentences introducing a procurement report. "
        f"The company searched for '{product_name}' with a target price of EGP {target_price:,.0f}. "
        f"They searched {platforms_str} and found {total_found} products. "
        f"Mention the value-for-money focus and the Egyptian market context. "
        f"Plain text only, no markdown, no bullet points."
    )

    result = _groq_call(prompt, max_tokens=200)
    if result:
        return result

    # Fallback template
    return (
        f"{company} conducted a procurement search for {product_name} across {platforms_str}, "
        f"targeting a budget of EGP {target_price:,.0f} per unit. "
        f"The search identified {total_found} candidate products, ranked by proximity to the target price "
        f"and overall value-for-money across seven weighted criteria. "
        f"This report presents the findings to support informed purchasing decisions in the Egyptian market."
    )

# 2- recommendation paragraph
def generate_recommendation(product_name: str,company: str,target_price: float,top_title: str,top_price: str,top_score: int,top_diff_pct: Optional[float],
    score_reasons: list[str],
) -> str:
    """
    Returns a recommendation paragraph for the top-ranked product.
    Saved as step_6_recommendation.json
    """
    diff_text = ""
    if top_diff_pct is not None:
        direction = "above" if top_diff_pct > 0 else "below"
        diff_text = f"It is {abs(top_diff_pct):.1f}% {direction} the target price. "

    reasons_text = "; ".join(score_reasons) if score_reasons else "high overall score across all criteria"

    prompt = (
        f"You are a senior procurement analyst at {company}. "
        f"Write exactly 2-3 sentences recommending the following product for purchase. "
        f"Product: '{top_title}'. "
        f"Price: EGP {top_price}. {diff_text}"
        f"Score: {top_score}/110. "
        f"Key reasons it ranked first: {reasons_text}. "
        f"Be confident and professional. Plain text only, no markdown, no lists."
    )

    result = _groq_call(prompt, max_tokens=200)
    if result:
        return result

    # Fallback template
    direction = "above" if (top_diff_pct or 0) > 0 else "below"
    diff_note = (
        f" at {abs(top_diff_pct or 0):.1f}% {direction} the target price of EGP {target_price:,.0f},"
        if top_diff_pct is not None else ","
    )
    return (
        f"Based on the seven-criterion scoring model, '{top_title}' is the recommended procurement choice{diff_note} "
        f"achieving a score of {top_score}/110 — the highest among all products evaluated. "
        f"It excels in: {reasons_text}."
    )

# 3- generate search queries for price extraction
def generate_search_queries(product_name: str, company: str, country: str, n: int = 10) -> list[str]:
    """
    Optional: ask the LLM to suggest additional search queries beyond the hardcoded ones.
    Returns list of query strings. Saved as step_1_queries.json
    """
    prompt = (
        f"You are a procurement specialist at {company} in {country}. "
        f"Generate {n} short, specific search queries to find '{product_name}' on Egyptian e-commerce sites "
        f"(amazon.eg, jumia.com.eg, noon.com). "
        f"Each query should target a different brand, type, or spec. "
        f"Return ONLY a JSON array of strings, nothing else. Example: [\"query1\", \"query2\"]"
    )
    raw = _groq_call(prompt, max_tokens=400)
    if not raw:
        return []
    try:
        import json, re
        # Strip any markdown fences
        clean = re.sub(r"```json|```", "", raw).strip()# Extract JSON array from the cleaned text
        queries = json.loads(clean)# Ensure it's a list of strings and return the top n
        if isinstance(queries, list):# Ensure it's a list of strings
            return [str(q) for q in queries[:n]]
    except Exception as e:
        logger.warning(f"Failed to parse LLM queries: {e}")
    return []
