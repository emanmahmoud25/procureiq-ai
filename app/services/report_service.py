"""
Report service — builds the full HTML procurement report.
Typography: Inter (body) + DM Mono (code/IDs). Clean, tight sizing.
"""
from datetime import datetime
from app.models.schemas import Product


def build_html_report(
    products: list[Product],
    company: str,
    product_name: str,
    target_price: float,
    introduction: str = "",
    recommendation: str = "",
) -> str:

    def score_bar(label, val, max_val, color):
        pct = int(val / max_val * 100) if max_val else 0
        return f"""
        <div style="margin-bottom:.4rem;">
          <div style="display:flex;justify-content:space-between;font-size:.68rem;margin-bottom:.12rem;">
            <span style="color:#8b949e;">{label}</span>
            <span style="color:{color};font-weight:500;">{val}/{max_val}</span>
          </div>
          <div style="background:#21262d;border-radius:999px;height:4px;">
            <div style="width:{pct}%;background:{color};border-radius:999px;height:4px;transition:width .6s ease;"></div>
          </div>
        </div>"""

    icons  = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    cards  = ""
    rows   = ""
    gen    = datetime.now().strftime("%d %B %Y — %H:%M")
    total  = len(products)

    for i, p in enumerate(products):
        title  = (p.product_title or "Product")[:65]
        price  = p.product_current_price
        url    = p.page_url or "#"
        desc   = (p.description or "")[:130]
        score  = p.score
        bd     = p.score_breakdown
        rank   = p.rank
        icon   = icons[i] if i < len(icons) else f"#{rank}"
        feat   = "featured" if rank == 1 else ""

        diff_pct = p.price_diff_pct
        if diff_pct is not None:
            diff_str   = f"{'↑' if diff_pct > 0 else '↓'} {abs(diff_pct):.1f}% vs target"
            diff_color = "#f0b429" if abs(diff_pct) > 15 else "#00d4aa"
        else:
            diff_str   = "Price not found"
            diff_color = "#f0b429"

        source = (
            "Amazon.eg"  if "amazon.eg"    in url else
            "Jumia.eg"   if "jumia.com.eg" in url else
            "Noon.eg"    if "noon.com"     in url else "Other"
        )

        bars = (
            score_bar("Price Available",       bd.price_available,       25, "#00d4aa") +
            score_bar("Price Competitiveness", bd.price_competitiveness, 25, "#0096ff") +
            score_bar("Proximity to Target",   bd.price_proximity,       25, "#a78bfa") +
            score_bar("Description Quality",   bd.description_quality,   10, "#f0b429") +
            score_bar("Has Image",             bd.has_image,              8, "#fb923c") +
            score_bar("Clear Title",           bd.clear_title,            4, "#34d399") +
            score_bar("Search Relevance",      bd.search_relevance,      13, "#60a5fa")
        )

        price_color = "#00d4aa" if price not in ("N/A","",None) else "#f0b429"
        price_d     = f"EGP {price}" if price not in ("N/A","",None) else "Check product page"

        img_html = ""
        if p.product_image_url:
            img_html = f'''
          <div style="width:100%;height:150px;border-radius:7px;overflow:hidden;
                      margin-bottom:.75rem;background:#21262d;display:flex;
                      align-items:center;justify-content:center;">
            <img src="{p.product_image_url}" alt="{title}"
                 style="max-width:100%;max-height:150px;object-fit:contain;"
                 onerror="this.parentElement.style.display=\'none\'">
          </div>'''

        cards += f"""
        <div class="product-card {feat}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.7rem;">
            <span style="font-size:1.5rem;">{icon}</span>
            <div style="text-align:right;">
              <span style="font-size:1.15rem;font-weight:600;color:#00d4aa;">{score}</span>
              <span style="font-size:.6rem;color:#8b949e;">/110</span>
              <div style="font-size:.62rem;color:#8b949e;margin-top:.08rem;">{source}</div>
            </div>
          </div>
          {img_html}
          <h3 style="font-size:.85rem;font-weight:600;margin:.5rem 0 .35rem;line-height:1.35;letter-spacing:-.01em;">{title}</h3>
          <p style="font-size:.75rem;color:#8b949e;margin-bottom:.65rem;line-height:1.55;">{desc or "See product page for full details."}</p>
          <div style="font-size:.9rem;font-weight:600;margin-bottom:.3rem;color:{price_color};">{price_d}</div>
          <div style="font-size:.7rem;color:{diff_color};margin-bottom:.6rem;">{diff_str}</div>
          <details class="score-details">
            <summary>Score breakdown</summary>
            <div style="margin-top:.55rem;">{bars}</div>
          </details>
          <a href="{url}" target="_blank" class="card-link">View on {source} →</a>
        </div>"""

        pct      = int(score / 110 * 100)
        top_b    = '<span class="top-badge">TOP PICK</span>' if rank == 1 else ""
        row_cls  = "top-row" if rank == 1 else ""
        price_td = (
            f'<span style="color:#00d4aa;font-weight:500;">EGP {price}</span>'
            if price not in ("N/A","",None)
            else '<span style="color:#f0b429;font-size:.75rem;">Check page</span>'
        )
        mini_bar = f"""
        <div style="display:flex;align-items:center;gap:.45rem;">
          <div style="flex:1;background:#21262d;border-radius:999px;height:4px;">
            <div style="width:{pct}%;background:#00d4aa;border-radius:999px;height:4px;"></div>
          </div>
          <span style="font-size:.68rem;color:#00d4aa;font-weight:500;">{score}/110</span>
        </div>"""

        rows += f"""
        <tr class="{row_cls}">
          <td class="rank-cell">#{rank}</td>
          <td><span class="product-name">{title}</span> {top_b}</td>
          <td><span class="source-tag">{source}</span></td>
          <td>{price_td}</td>
          <td style="font-size:.72rem;color:{diff_color};">{diff_str}</td>
          <td style="min-width:120px;">{mini_bar}</td>
          <td><a href="{url}" target="_blank" class="view-btn">View →</a></td>
        </tr>"""

    top      = products[0] if products else None
    top_t    = (top.product_title or "N/A")[:80] if top else "N/A"
    top_p    = top.product_current_price if top else "N/A"
    top_url  = top.page_url or "#" if top else "#"
    top_desc = (top.description or "")[:260] if top else ""
    top_sc   = top.score if top else 0
    top_pd   = f"EGP {top_p}" if top_p not in ("N/A","",None) else "Check product page"
    top_pc   = "#00d4aa" if top_p not in ("N/A","",None) else "#f0b429"
    top_img_html = (
        f'<img src="{top.product_image_url}" alt="Top Product" '
        'style="max-width:160px;max-height:130px;object-fit:contain;'
        'border-radius:7px;margin-bottom:.65rem;background:#21262d;padding:8px;" '
        'onerror="this.style.display=\'none\'">'
    ) if (top and top.product_image_url) else ""

    rec_text = recommendation or (
        f"Based on the seven-criterion scoring model, '{top_t}' achieved the highest overall score "
        f"of {top_sc}/110, making it the recommended procurement choice for {company}."
    )
    intro_html = (
        f'<div class="intro-block"><p>{introduction}</p></div>'
        if introduction else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{company} — {product_name.title()} Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --dark:#0d1117;--dark2:#161b22;--dark3:#21262d;
      --accent:#00d4aa;--purple:#a78bfa;--gold:#f0b429;
      --text:#e6edf3;--muted:#8b949e;--border:rgba(255,255,255,.08);--radius:11px;
      --fs-xs:.72rem;--fs-sm:.82rem;--fs-base:.9rem;
      --fw-normal:400;--fw-medium:500;--fw-semi:600;
    }}
    body{{font-family:'Inter',system-ui,sans-serif;font-size:var(--fs-base);font-weight:var(--fw-normal);background:var(--dark);color:var(--text);line-height:1.6}}

    /* NAV */
    .top-nav{{background:var(--dark2);border-bottom:1px solid var(--border);padding:.6rem 1.75rem;display:flex;gap:.75rem;align-items:center}}
    .top-nav a{{color:var(--muted);text-decoration:none;font-size:var(--fs-sm);font-weight:var(--fw-medium);padding:.28rem .65rem;border-radius:6px;transition:color .2s,background .2s}}
    .top-nav a:hover{{color:var(--accent);background:rgba(0,212,170,.08)}}
    .top-nav-brand{{font-size:.88rem;font-weight:var(--fw-semi);color:var(--accent);margin-right:auto;letter-spacing:-.01em}}

    /* HERO */
    .hero{{background:linear-gradient(135deg,#0d1117 0%,#0a2540 50%,#0d1117 100%);border-bottom:1px solid var(--border);padding:3.5rem 2rem 2.5rem;text-align:center}}
    .hero-badge{{display:inline-block;background:rgba(0,212,170,.12);border:1px solid rgba(0,212,170,.22);color:var(--accent);font-size:var(--fs-xs);font-weight:var(--fw-semi);letter-spacing:.1em;text-transform:uppercase;padding:.28rem .85rem;border-radius:999px;margin-bottom:1.1rem}}
    .hero h1{{font-size:clamp(1.6rem,3.5vw,2.6rem);font-weight:var(--fw-semi);letter-spacing:-.02em;margin-bottom:.6rem}}
    .hero h1 span{{color:var(--accent)}}
    .hero-sub{{color:var(--muted);font-size:var(--fs-sm);margin-bottom:.9rem}}
    .target-badge{{display:inline-block;background:rgba(167,139,250,.12);border:1px solid rgba(167,139,250,.25);color:var(--purple);font-size:var(--fs-sm);font-weight:var(--fw-medium);padding:.38rem 1.2rem;border-radius:999px}}
    .hero-stats{{display:flex;gap:1.75rem;justify-content:center;flex-wrap:wrap;margin-top:1.75rem}}
    .stat{{text-align:center}}
    .stat-num{{font-size:1.65rem;font-weight:var(--fw-semi);color:var(--accent);display:block;letter-spacing:-.01em}}
    .stat-label{{font-size:var(--fs-xs);color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}

    /* INTRO */
    .intro-block{{background:var(--dark2);border:1px solid var(--border);border-left:2px solid var(--accent);border-radius:var(--radius);padding:1.35rem 1.75rem;margin-bottom:2rem;font-size:var(--fs-sm);line-height:1.8;color:#c9d1d9}}

    /* LAYOUT */
    .container{{max-width:1060px;margin:0 auto;padding:2.5rem 1.5rem}}
    .section{{margin-bottom:2.75rem}}
    .section-header{{display:flex;align-items:center;gap:.65rem;margin-bottom:1.35rem;padding-bottom:.9rem;border-bottom:1px solid var(--border)}}
    .section-icon{{width:32px;height:32px;background:rgba(0,212,170,.12);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.9rem}}
    .section-title{{font-size:var(--fs-base);font-weight:var(--fw-semi);letter-spacing:-.01em}}

    /* CARDS */
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:1.1rem}}
    .product-card{{background:var(--dark2);border:1px solid var(--border);border-radius:var(--radius);padding:1.35rem;transition:transform .2s,border-color .2s}}
    .product-card:hover{{transform:translateY(-3px);border-color:rgba(0,212,170,.28)}}
    .product-card.featured{{border-color:var(--accent);background:linear-gradient(135deg,rgba(0,212,170,.05),var(--dark2))}}
    .score-details{{margin-bottom:.85rem;border:1px solid var(--border);border-radius:7px;padding:.45rem .7rem}}
    .score-details summary{{font-size:var(--fs-xs);color:var(--muted);cursor:pointer;user-select:none}}
    .score-details summary:hover{{color:var(--accent)}}
    .card-link{{display:inline-block;background:rgba(0,212,170,.1);border:1px solid rgba(0,212,170,.25);color:var(--accent);font-size:var(--fs-xs);font-weight:var(--fw-medium);padding:.32rem .8rem;border-radius:6px;text-decoration:none}}
    .card-link:hover{{background:rgba(0,212,170,.18)}}

    /* TABLE */
    .table-wrap{{background:var(--dark2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
    table{{width:100%;border-collapse:collapse}}
    thead tr{{background:var(--dark3)}}
    th{{font-size:.65rem;font-weight:var(--fw-semi);text-transform:uppercase;letter-spacing:.08em;color:var(--muted);padding:.8rem 1.1rem;text-align:left}}
    td{{padding:.75rem 1.1rem;font-size:var(--fs-sm);border-top:1px solid var(--border)}}
    tr.top-row td{{background:rgba(0,212,170,.03)}}
    .rank-cell{{font-weight:var(--fw-semi);color:var(--muted);width:44px}}
    tr.top-row .rank-cell{{color:var(--accent)}}
    .top-badge{{display:inline-block;background:rgba(240,180,41,.12);border:1px solid rgba(240,180,41,.25);color:var(--gold);font-size:.58rem;font-weight:var(--fw-semi);text-transform:uppercase;padding:.14rem .45rem;border-radius:4px;margin-left:.35rem;vertical-align:middle;letter-spacing:.06em}}
    .source-tag{{font-size:.65rem;background:var(--dark3);border:1px solid var(--border);color:var(--muted);padding:.14rem .45rem;border-radius:4px}}
    .product-name{{font-weight:var(--fw-medium)}}
    .view-btn{{display:inline-block;border:1px solid var(--border);color:var(--text);font-size:.7rem;padding:.24rem .65rem;border-radius:6px;text-decoration:none;transition:border-color .2s,color .2s}}
    .view-btn:hover{{border-color:var(--accent);color:var(--accent)}}

    /* RECOMMENDATION */
    .recommendation{{background:linear-gradient(135deg,rgba(0,212,170,.06),rgba(0,150,255,.03));border:1px solid rgba(0,212,170,.22);border-radius:var(--radius);padding:1.75rem;display:grid;grid-template-columns:1fr auto;gap:1.35rem;align-items:start}}
    .rec-label{{font-size:.65rem;font-weight:var(--fw-semi);text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin-bottom:.4rem}}
    .rec-title{{font-size:1.2rem;font-weight:var(--fw-semi);margin-bottom:.45rem;line-height:1.25;letter-spacing:-.01em}}
    .rec-text{{color:#c9d1d9;font-size:var(--fs-sm);line-height:1.75;margin-bottom:.85rem;border-left:2px solid var(--purple);padding-left:.9rem}}
    .rec-price{{font-size:1.35rem;font-weight:var(--fw-semi);margin-top:.35rem;letter-spacing:-.01em}}
    .rec-cta{{display:inline-block;background:var(--accent);color:#0d1117;font-weight:var(--fw-semi);font-size:var(--fs-sm);padding:.65rem 1.5rem;border-radius:8px;text-decoration:none;transition:opacity .2s;margin-top:.5rem;white-space:nowrap}}
    .rec-cta:hover{{opacity:.85}}

    /* LEGEND */
    .legend{{background:var(--dark2);border:1px solid var(--border);border-radius:var(--radius);padding:1.1rem 1.35rem;margin-bottom:1.75rem}}
    .legend-title{{font-size:var(--fs-xs);font-weight:var(--fw-semi);margin-bottom:.6rem;color:var(--accent);text-transform:uppercase;letter-spacing:.08em}}
    .legend-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:.38rem .65rem;font-size:var(--fs-xs)}}
    .legend-item{{display:flex;align-items:center;gap:.35rem;color:var(--muted)}}
    .legend-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}

    .footer{{text-align:center;padding:1.75rem;color:var(--muted);font-size:var(--fs-xs);border-top:1px solid var(--border)}}

    @media(max-width:640px){{.recommendation{{grid-template-columns:1fr}}.hero-stats{{gap:1.25rem}}}}
  </style>
</head>
<body>

<nav class="top-nav">
  <span class="top-nav-brand">{company} Procurement</span>
  <a href="/">← New Search</a>
  <a href="/history">History</a>
</nav>

<header class="hero">
  <div class="hero-badge">Procurement Intelligence Report</div>
  <h1>{company} — <span>{product_name.title()}</span></h1>
  <p class="hero-sub">Egypt Market · {gen}</p>
  <div class="target-badge">Target Price: EGP {target_price:,.0f}</div>
  <div class="hero-stats">
    <div class="stat"><span class="stat-num">{total}</span><span class="stat-label">Products Found</span></div>
    <div class="stat"><span class="stat-num">3</span><span class="stat-label">Platforms</span></div>
    <div class="stat"><span class="stat-num">110</span><span class="stat-label">Max Score</span></div>
    <div class="stat"><span class="stat-num">7</span><span class="stat-label">Criteria</span></div>
  </div>
</header>

<main class="container">

  {intro_html}

  <div class="legend">
    <div class="legend-title">Scoring Criteria (110 points total)</div>
    <div class="legend-grid">
      <div class="legend-item"><div class="legend-dot" style="background:#00d4aa;"></div>Price Available (25 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#0096ff;"></div>Price Competitiveness (25 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#a78bfa;"></div>Proximity to Target (25 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f0b429;"></div>Description Quality (10 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fb923c;"></div>Has Image (8 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#34d399;"></div>Clear Title (4 pts)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#60a5fa;"></div>Search Relevance (13 pts)</div>
    </div>
  </div>

  <section class="section">
    <div class="section-header"><div class="section-icon">📦</div><h2 class="section-title">Products Overview</h2></div>
    <div class="cards-grid">{cards}</div>
  </section>

  <section class="section">
    <div class="section-header"><div class="section-icon">💰</div><h2 class="section-title">Price Comparison — Target EGP {target_price:,.0f}</h2></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Rank</th><th>Product</th><th>Source</th><th>Price</th><th>vs Target</th><th>Score</th><th>Link</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-header"><div class="section-icon">⭐</div><h2 class="section-title">Top Recommendation</h2></div>
    <div class="recommendation">
      <div>
        <p class="rec-label">Best Value Pick · Score {top_sc}/110</p>
        <h3 class="rec-title">{top_t}</h3>
        {top_img_html}
        <p class="rec-text">{rec_text}</p>
        <div class="rec-price" style="color:{top_pc};">{top_pd}</div>
      </div>
      <div style="text-align:center;">
        <a href="{top_url}" target="_blank" class="rec-cta">View Product →</a>
      </div>
    </div>
  </section>

</main>

<footer class="footer">Generated by {company} Procurement AI &nbsp;·&nbsp; {gen}</footer>
</body>
</html>"""