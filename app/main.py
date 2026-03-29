import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
import app.storage.db_store as store

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup
    from app.models.database import engine, Base
    import app.models.db_models  # noqa: F401 — registers ORM models
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    yield
    # Shutdown — add cleanup here if needed


# ── App instance (MUST come after lifespan definition) ────────────────────────
app = FastAPI(
    title="Procurement Search API",
    description="Egypt e-commerce procurement intelligence with full session storage",
    version="3.0.0",
    lifespan=lifespan,          # ← هنا بدل @app.on_event
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers.search import router as search_router  # noqa: E402
app.include_router(search_router)


# ── Helpers ───────────────────────────────────────────────────────────────────
import os
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

def _read_template(name: str) -> str:
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── UI pages ──────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return HTMLResponse(_read_template("index.html"))

@app.get("/history", response_class=HTMLResponse, include_in_schema=False)
def history_page():
    return HTMLResponse(_read_template("history.html"))


# ── Report ────────────────────────────────────────────────────────────────────
@app.get("/report/{session_id}", response_class=HTMLResponse)
def get_report(session_id: str):
    html = store.get_report_html(session_id)  
    if not html:
        raise HTTPException(status_code=404, detail=f"Report for '{session_id}' not found")
    return HTMLResponse(html)  


# ── Storage API ───────────────────────────────────────────────────────────────
@app.get("/api/sessions")
def api_list_sessions(limit: int = 100):
    return store.list_sessions(limit=limit)

@app.get("/api/sessions/{session_id}")
def api_get_session(session_id: str):
    meta = store.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    return meta

@app.get("/api/sessions/{session_id}/steps")
def api_get_steps(session_id: str):
    steps = store.get_all_steps(session_id)
    if not steps and not store.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return steps

@app.get("/api/sessions/{session_id}/steps/{step_number}")
def api_get_step(session_id: str, step_number: int):
    step = store.get_step(session_id, step_number)
    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_number} not found")
    return step

@app.get("/api/stats")
def api_stats():
    return store.get_stats()


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    stats = store.get_stats()
    return {"status": "ok", "version": "3.0.0", **stats}