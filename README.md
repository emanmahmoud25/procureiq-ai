# ProcureIQ AI 🛒

> AI-powered procurement intelligence system for the Egyptian e-commerce market.  
> Give it a product and a budget — it searches, scores, and reports automatically.

---

## The Idea

Procurement teams waste hours manually comparing prices across multiple platforms.  
**ProcureIQ AI** solves this by acting as an autonomous procurement agent:

1. You type a product name and your target budget
2. The system searches **Amazon.eg, Jumia.eg, and Noon.eg** simultaneously
3. It extracts real prices and product images using AI
4. It scores every product across **7 criteria** and ranks them
5. It generates a **professional HTML report** with an AI-written recommendation
6. Everything is saved to a database for full audit history

**Result:** A complete procurement decision in under 2 minutes instead of 2 hours.

---

## The 7-Step Agent Pipeline

Every search triggers 7 sequential agents — each step is saved to PostgreSQL:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                               │
│          Product Name + Target Price + Tolerance %              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1 — LLM Query Generation                                  │
│  Groq LLaMA 3.1 generates smart search queries                  │
│  e.g. "coffee machine price EGP site:amazon.eg"                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2 — Web Search                                            │
│  Tavily fires all queries across Amazon.eg, Jumia.eg, Noon.eg   │
│  Collects up to 80 raw results with URLs, titles, snippets      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3 — Product Build                                         │
│  For each product URL:                                          │
│    Price → 4-step strategy (extract → SERP → alt → generic)    │
│    Image → 4-step strategy (result.image → SERP → alt → Amazon)│
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4 — Scoring & Ranking                                     │
│  Every product scored across 7 criteria (110 points max)        │
│  Price proximity to your target budget is the KEY factor        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5 — LLM Introduction                                      │
│  Groq writes a professional market overview paragraph           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6 — LLM Recommendation                                    │
│  Groq analyzes the top product and writes why it's the          │
│  best procurement choice for your company                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7 — Output                                                │
│  Full HTML report generated + saved to PostgreSQL               │
│  Session history available at /history                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scoring Model (110 Points Total)

| Criterion | Points | Logic |
|-----------|--------|-------|
| Price Available | 25 | Full points if a real price was found |
| **Price Proximity to Target** | **25** | **KEY** — within 5% of budget = full points |
| Price Competitiveness | 25 | Cheapest product among all results scores highest |
| Description Quality | 10 | Longer, detailed descriptions score higher |
| Has Product Image | 8 | Product image successfully fetched = 8 pts |
| Clear Title | 4 | Meaningful, non-junk product title |
| Search Relevance | 13 | Based on Tavily relevance score |

> **Key Design Principle:** Price Proximity rewards products closest to the buyer's budget —
> not just the cheapest, not just the most expensive. The product that best matches your target wins.

---

## Price & Image Extraction Strategy

The system never gives up — it tries 4 strategies before returning empty:

### Price Strategy
```
1. extract()        → Scrape the product page directly (most accurate)
2. SERP snippet     → Google snippet from same site (Amazon/Jumia/Noon)
3. Alt sites        → Try the other 2 platforms as fallback
4. Generic search   → Search without site restriction (last resort)
```

### Image Strategy
```
1. result.image     → Image embedded in search result
2. SERP images      → Images from search results page
3. Alt sites        → Try other platforms for same product
4. Amazon fallback  → Broad Amazon search as last resort
```

---

## Project Structure

```
procurement-api/
├── app/
│   ├── clients/
│   │   └── tavily_client.py       ← Tavily search / price / image client
│   │                                 (4-step price + 4-step image strategy)
│   ├── core/
│   │   └── config.py              ← All settings loaded from .env
│   ├── models/
│   │   ├── database.py            ← SQLAlchemy engine + session factory
│   │   ├── db_models.py           ← ORM models (Session, Step, Report)
│   │   └── schemas.py             ← Pydantic request/response schemas
│   ├── routers/
│   │   └── search.py              ← Orchestrates all 7 agent steps
│   ├── services/
│   │   ├── llm_service.py         ← Groq LLaMA 3.1: queries + intro + rec
│   │   ├── report_service.py      ← HTML report builder
│   │   ├── scoring_service.py     ← 7-criterion scoring + ranking logic
│   │   └── search_service.py      ← Tavily queries + product build
│   ├── storage/
│   │   ├── db_store.py            ← PostgreSQL session/step/report storage
│   │   └── store.py               ← Legacy JSON file storage
│   ├── templates/
│   │   ├── history.html           ← Session history UI
│   │   └── index.html             ← Search UI
│   └── main.py                    ← FastAPI app + lifespan + all routes
├── Docker/
│   ├── .env                       ← Environment variables (not committed)
│   ├── .env.example               ← Template for .env
│   ├── docker-compose.yml         ← API + PostgreSQL + pgAdmin services
│   └── requirements.txt           ← Python dependencies
├── runs/                          ← Legacy JSON session files
├── tests/
├── .env.example
└── .gitignore
```

---

## Features

- 🔍 **Multi-platform search** — Amazon.eg, Jumia.eg, Noon.eg simultaneously
- 💰 **Smart price extraction** — 4-step fallback, near-zero null prices
- 🖼 **Product image fetching** — 4-step fallback across all platforms
- 📊 **7-criterion scoring** — 110-point model, price proximity is key
- 🤖 **LLM-powered reports** — Groq LLaMA 3.1 writes intro + recommendation
- 💾 **Full session history** — every step saved to PostgreSQL
- 📄 **HTML report** — professional procurement report per session
- 🐳 **Docker ready** — one command to run everything

---

## Quick Start (Docker — Recommended)

### 1. Clone & configure

```bash
git clone https://github.com/your-repo/procurement-api.git
cd procurement-api/Docker
cp .env.example .env
```

### 2. Edit `.env`

```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxx
DATABASE_URL=postgresql://procurement:procurement123@db:5432/procurement_db
SCORE_THRESHOLD=0.10
TOP_PICKS=10
SEARCH_DELAY=2.0
PRICE_SEARCH_DELAY=2.0
IMAGE_SEARCH_DELAY=2.0
```

### 3. Run

```bash
docker-compose up --build
```

### 4. Open in browser

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Search UI |
| http://localhost:8000/history | Session history |
| http://localhost:8000/docs | Swagger API docs |
| http://localhost:5050 | pgAdmin — DB manager |

> pgAdmin login: `admin@admin.com` / `admin123`

---

## Quick Start (Local — No Docker)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r Docker/requirements.txt

# 3. Configure
cp .env.example .env
# Add TAVILY_API_KEY, GROQ_API_KEY, DATABASE_URL

# 4. Run
uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Search UI |
| `GET` | `/history` | Session history UI |
| `POST` | `/search` | **Main** — runs all 7 agent steps |
| `GET` | `/report/{session_id}` | View HTML report |
| `GET` | `/api/sessions` | List all sessions (JSON) |
| `GET` | `/api/sessions/{id}` | Session metadata |
| `GET` | `/api/sessions/{id}/steps` | All saved agent steps |
| `GET` | `/api/sessions/{id}/steps/{n}` | Specific step data |
| `GET` | `/api/stats` | Aggregate stats |
| `GET` | `/health` | Health check |

### Search Request Example

```json
POST /search
{
  "product_name": "standing desk",
  "target_price": 5000,
  "price_tolerance_pct": 30,
  "company_name": "TechSphere",
  "top_picks": 10
}
```

---

## Database Schema

### SessionRecord
```
session_id      TEXT PRIMARY KEY
product_name    TEXT
price_min       FLOAT
price_max       FLOAT
status          TEXT        ← running / done / failed
total_found     INT
in_range_count  INT
started_at      TIMESTAMP
finished_at     TIMESTAMP
error           TEXT
```

### StepRecord
```
id              SERIAL PRIMARY KEY
session_id      TEXT  → FK SessionRecord
step            INT   ← 1 to 7
label           TEXT  ← queries / search_results / products / ...
data            JSON  ← full step output
saved_at        TIMESTAMP
```

### ReportRecord
```
session_id      TEXT PRIMARY KEY → FK SessionRecord
html            TEXT  ← full HTML report
```

---

## Docker Services

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| API | `procurement_api` | 8000 | FastAPI application |
| Database | `procurement_db` | 5432 | PostgreSQL 16 Alpine |
| pgAdmin | `procurement_pgadmin` | 5050 | DB management UI |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAVILY_API_KEY` | ✅ Yes | — | From [tavily.com](https://tavily.com) |
| `GROQ_API_KEY` | Recommended | — | From [console.groq.com](https://console.groq.com) |
| `DATABASE_URL` | ✅ Yes | — | PostgreSQL connection string |
| `TOP_PICKS` | No | `10` | Max products to process per search |
| `SCORE_THRESHOLD` | No | `0.10` | Min Tavily score to include result |
| `SEARCH_DELAY` | No | `2.0` | Seconds between search calls |
| `PRICE_SEARCH_DELAY` | No | `2.0` | Seconds between price fetch calls |
| `IMAGE_SEARCH_DELAY` | No | `2.0` | Seconds between image fetch calls |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI + Uvicorn |
| AI Search | Tavily API |
| LLM | Groq — LLaMA 3.1 8B Instant |
| Database | PostgreSQL 16 + SQLAlchemy |
| Validation | Pydantic v2 |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

