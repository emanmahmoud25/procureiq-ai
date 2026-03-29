"""
JSON-file storage engine — saves every agent step + HTML report + session metadata.

Folder layout:
  runs/
  ├── index.json                          ← master list of all sessions
  └── 20250324_142305_a3f9bc/
      ├── meta.json                       ← status, product, target_price, timestamps
      ├── step_1_queries.json             ← Agent 1: LLM-generated search queries
      ├── step_2_search_results.json      ← Agent 2: raw Tavily results
      ├── step_3_products.json            ← Agent 3: built product dicts (price + image)
      ├── step_4_scored.json              ← Agent 4: scored + ranked products
      ├── step_5_introduction.json        ← Agent 5: LLM intro paragraph
      ├── step_6_recommendation.json      ← Agent 6: LLM recommendation text
      └── step_7_report.html              ← Final HTML report
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional
from filelock import FileLock


RUNS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "runs")
INDEX_FILE = os.path.join(RUNS_DIR, "index.json")


# ── helpers ────────────────────────────────────────────────────────────────────

def _ensure_dirs():
    os.makedirs(RUNS_DIR, exist_ok=True)


def _session_dir(session_id: str) -> str:
    return os.path.join(RUNS_DIR, session_id)


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _read_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _update_index(session_id: str, meta: dict):
    """Thread-safe update of the master index.json."""
    _ensure_dirs()
    lock_path = INDEX_FILE + ".lock"
    with FileLock(lock_path):
        index = _read_json(INDEX_FILE) or []
        # Replace existing entry or append
        updated = False
        for i, entry in enumerate(index):
            if entry.get("session_id") == session_id:
                index[i] = {**entry, **meta}
                updated = True
                break
        if not updated:
            index.insert(0, meta)
        _write_json(INDEX_FILE, index)


# ── public API ─────────────────────────────────────────────────────────────────

def new_session(product_name: str, target_price: float, company: str = "TechSphere") -> str:
    """
    Create a new session folder and register it in index.json.
    Returns the session_id (timestamp + short UUID).
    """
    _ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = str(uuid.uuid4())[:6]
    session_id = f"{ts}_{short_id}"

    os.makedirs(_session_dir(session_id), exist_ok=True)

    meta = {
        "session_id":   session_id,
        "product_name": product_name,
        "target_price": target_price,
        "company":      company,
        "status":       "running",
        "started_at":   datetime.now().isoformat(),
        "finished_at":  None,
        "total_products": 0,
        "top_product":  None,
        "top_score":    0,
    }
    _write_json(os.path.join(_session_dir(session_id), "meta.json"), meta)
    _update_index(session_id, meta)
    return session_id


def save_step(session_id: str, step_number: int, label: str, data: Any):
    """
    Persist the output of one agent step.

    step_number : 1-7
    label       : human-readable name, e.g. "search_queries"
    data        : any JSON-serialisable object
    """
    filename = f"step_{step_number}_{label}.json"
    path = os.path.join(_session_dir(session_id), filename)
    payload = {
        "step":       step_number,
        "label":      label,
        "saved_at":   datetime.now().isoformat(),
        "data":       data,
    }
    _write_json(path, payload)


def save_report(session_id: str, html: str):
    """Save the final HTML report."""
    path = os.path.join(_session_dir(session_id), "step_7_report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def finish_session(session_id: str, total_products: int, top_product: Optional[str], top_score: int):
    """Mark session as completed and update index."""
    meta_path = os.path.join(_session_dir(session_id), "meta.json")
    meta = _read_json(meta_path) or {}
    meta.update({
        "status":         "completed",
        "finished_at":    datetime.now().isoformat(),
        "total_products": total_products,
        "top_product":    top_product,
        "top_score":      top_score,
    })
    _write_json(meta_path, meta)
    _update_index(session_id, meta)


def fail_session(session_id: str, error: str):
    """Mark session as failed."""
    meta_path = os.path.join(_session_dir(session_id), "meta.json")
    meta = _read_json(meta_path) or {}
    meta.update({
        "status":      "failed",
        "finished_at": datetime.now().isoformat(),
        "error":       error,
    })
    _write_json(meta_path, meta)
    _update_index(session_id, meta)


# ── read helpers ──────────────────────────────────────────────────────────────

def list_sessions(limit: int = 50) -> list[dict]:
    """Return latest N sessions from index.json."""
    index = _read_json(INDEX_FILE) or []
    return index[:limit]


def get_session(session_id: str) -> Optional[dict]:
    """Return meta.json for a specific session."""
    return _read_json(os.path.join(_session_dir(session_id), "meta.json"))


def get_step(session_id: str, step_number: int) -> Optional[dict]:
    """Return a specific step file for a session."""
    folder = _session_dir(session_id)
    for fname in os.listdir(folder):
        if fname.startswith(f"step_{step_number}_") and fname.endswith(".json"):
            return _read_json(os.path.join(folder, fname))
    return None


def get_all_steps(session_id: str) -> list[dict]:
    """Return all step JSON files for a session, sorted by step number"""
    folder = _session_dir(session_id)
    if not os.path.exists(folder):
        return []
    steps = []
    for fname in sorted(os.listdir(folder)):
        if fname.startswith("step_") and fname.endswith(".json"):
            data = _read_json(os.path.join(folder, fname))
            if data:
                steps.append(data)
    return steps


def get_report_path(session_id: str) -> Optional[str]:
    """Return path to the HTML report if it exists."""
    path = os.path.join(_session_dir(session_id), "step_7_report.html")
    return path if os.path.exists(path) else None


def get_stats() -> dict:
    """Aggregate stats across all sessions."""
    index = _read_json(INDEX_FILE) or []
    total   = len(index)
    done    = sum(1 for s in index if s.get("status") == "completed")
    failed  = sum(1 for s in index if s.get("status") == "failed")
    running = sum(1 for s in index if s.get("status") == "running")
    total_products = sum(s.get("total_products", 0) for s in index)
    return {
        "total_searches":  total,
        "completed":       done,
        "failed":          failed,
        "running":         running,
        "total_products":  total_products,
    }
