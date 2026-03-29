"""
Search router — orchestrates all 7 agent steps and persists each one.

Step 1 : LLM-generated search queries         → step_1_queries.json
Step 2 : Raw Tavily search results             → step_2_search_results.json
Step 3 : Built product dicts (price + image)   → step_3_products.json
Step 4 : Scored + ranked products              → step_4_scored.json
Step 5 : LLM introduction paragraph           → step_5_introduction.json
Step 6 : LLM recommendation paragraph         → step_6_recommendation.json
Step 7 : Final HTML report                     → step_7_report.html
"""
import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import SearchRequest, SearchResponse, Product
from app.services.search_service import SearchService
from app.services.scoring_service import score_products
from app.services.report_service import build_html_report
from app.services.llm_service import (
    generate_search_queries,
    generate_introduction,
    generate_recommendation,
)
from app.core.config import get_settings
import app.storage.db_store as store

logger   = logging.getLogger(__name__)
router   = APIRouter()
settings = get_settings()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search for products matching a target price",
    description="""
Searches configured target sites for the given product,
scores results across 7 criteria (price proximity to target is key),
generates LLM introduction + recommendation, and saves every step to disk.

Returns ranked products + a link to the full HTML report.
    """,
)
async def search_products(request: SearchRequest):
    # ── Create session ────────────────────────────────────────────────────────
    session_id = store.new_session(
        product_name=request.product_name,
        target_price=request.target_price,
        company=request.company_name,
    )
    logger.info(f"[{session_id}] START  product='{request.product_name}'  target=EGP {request.target_price}")

    try:
        search_svc   = SearchService()
        target_sites = settings.target_sites  
        platforms_used = [s.split(".")[0].capitalize() for s in target_sites]

        # ── STEP 1 : LLM search queries ───────────────────────────────────────
        logger.info(f"[{session_id}] Step 1 — generating LLM search queries")
        llm_queries = generate_search_queries(
            product_name=request.product_name,
            company=request.company_name,
            country=request.country,
            n=8,
        )
        store.save_step(session_id, 1, "queries", {
            "llm_queries":  llm_queries,
            "product_name": request.product_name,
            "target_price": request.target_price,
            "country":      request.country,
        })

        # ── STEP 2 : Tavily search ────────────────────────────────────────────
        logger.info(f"[{session_id}] Step 2 — running Tavily searches")
        search_results = search_svc.run_searches(request.product_name)
        store.save_step(session_id, 2, "search_results", {
            "total":   len(search_results),
            "results": [r.dict() for r in search_results],
        })
        logger.info(f"[{session_id}] Step 2 done — {len(search_results)} results")

        # ── STEP 3 : Build products ───────────────────────────────────────────
        logger.info(f"[{session_id}] Step 3 — building product data")

        per_site = max(2, request.top_picks // len(target_sites))

        top_results = []
        seen_urls: set[str] = set()

        for site in target_sites:
            site_results = [
                r for r in search_results
                if site in r.url and r.url not in seen_urls
            ][:per_site]
            for r in site_results:
                seen_urls.add(r.url)
            top_results.extend(site_results)

        shortage = request.top_picks - len(top_results)
        if shortage > 0:
            extras = [
                r for r in search_results
                if r.url not in seen_urls
                and any(s in r.url for s in target_sites)
            ][:shortage]
            if extras:
                extra_sources = set(
                    next((s for s in target_sites if s in r.url), "unknown")
                    for r in extras
                )
                logger.info(f"[{session_id}] Filling {shortage} slots from: {extra_sources}")
            top_results.extend(extras)
            seen_urls.update(r.url for r in extras)

        if len(top_results) < request.top_picks:
            last_resort = [
                r for r in search_results
                if r.url not in seen_urls
            ][:request.top_picks - len(top_results)]
            if last_resort:
                logger.info(f"[{session_id}] Last resort: adding {len(last_resort)} more results")
            top_results.extend(last_resort)

        dist = {site: sum(1 for r in top_results if site in r.url) for site in target_sites}
        logger.info(f"[{session_id}] Sites distribution: {' | '.join(f'{k}={v}' for k, v in dist.items())}")

        products: list[Product] = []
        for r in top_results:
            logger.info(f"[{session_id}]   processing: {r.url[:60]}")
            prod = search_svc.build_product(r)
            if prod.product_title != "N/A":
                products.append(prod)

        store.save_step(session_id, 3, "products", {
            "total":    len(products),
            "products": [p.dict() for p in products],
        })
        logger.info(f"[{session_id}] Step 3 done — {len(products)} products built")

        # ── STEP 4 : Score & rank ─────────────────────────────────────────────
        logger.info(f"[{session_id}] Step 4 — scoring products")
        ranked = score_products(
            products,
            search_results,
            target_price=request.target_price,
            price_tolerance_pct=request.price_tolerance_pct,
        )
        store.save_step(session_id, 4, "scored", {
            "target_price":        request.target_price,
            "price_tolerance_pct": request.price_tolerance_pct,
            "ranked_products":     [p.dict() for p in ranked],
        })
        logger.info(f"[{session_id}] Step 4 done — top score: {ranked[0].score if ranked else 0}")

        # ── STEP 5 : LLM Introduction ─────────────────────────────────────────
        logger.info(f"[{session_id}] Step 5 — generating introduction")
        introduction = generate_introduction(
            product_name=request.product_name,
            company=request.company_name,
            target_price=request.target_price,
            total_found=len(ranked),
            platforms=platforms_used,
        )
        store.save_step(session_id, 5, "introduction", {"text": introduction})

        # ── STEP 6 : LLM Recommendation ──────────────────────────────────────
        logger.info(f"[{session_id}] Step 6 — generating recommendation")
        top = ranked[0] if ranked else None
        score_reasons: list[str] = []
        if top:
            bd = top.score_breakdown
            if bd.price_proximity       >= 20: score_reasons.append("closest price to target")
            if bd.price_competitiveness >= 20: score_reasons.append("most competitive price among all results")
            if bd.description_quality   >= 8:  score_reasons.append("detailed product description")
            if bd.has_image             >= 6:  score_reasons.append("product image available")
            if bd.search_relevance      >= 10: score_reasons.append("high search relevance")

        recommendation = generate_recommendation(
            product_name=request.product_name,
            company=request.company_name,
            target_price=request.target_price,
            top_title=top.product_title if top else "N/A",
            top_price=top.product_current_price if top else "N/A",
            top_score=top.score if top else 0,
            top_diff_pct=top.price_diff_pct if top else None,
            score_reasons=score_reasons,
        )
        store.save_step(session_id, 6, "recommendation", {
            "text":          recommendation,
            "score_reasons": score_reasons,
            "top_product":   top.product_title if top else None,
            "top_price":     top.product_current_price if top else None,
            "top_score":     top.score if top else 0,
        })

        # ── STEP 7 : HTML Report ──────────────────────────────────────────────
        logger.info(f"[{session_id}] Step 7 — building HTML report")
        html = build_html_report(
            products=ranked,
            company=request.company_name,
            product_name=request.product_name,
            target_price=request.target_price,
            introduction=introduction,
            recommendation=recommendation,
        )
        store.save_report(session_id, html)

        # ── Finish session ────────────────────────────────────────────────────
        store.finish_session(
            session_id=session_id,
            total_products=len(ranked),
            top_product=top.product_title if top else None,
            top_score=top.score if top else 0,
        )

        logger.info(f"[{session_id}] DONE  — {len(ranked)} products, session saved")

        return SearchResponse(
            job_id=session_id,
            status="completed",
            product_name=request.product_name,
            target_price=request.target_price,
            total_found=len(ranked),
            products=ranked,
            report_url=f"/report/{session_id}",
            introduction=introduction,
            recommendation=recommendation,
        )

    except Exception as e:
        store.fail_session(session_id, str(e))
        logger.error(f"[{session_id}] FAILED: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))