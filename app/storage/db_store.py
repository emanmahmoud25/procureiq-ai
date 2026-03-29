import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.db_models import SessionRecord, StepRecord, ReportRecord


def _to_json(data) -> dict:
    """Convert any Pydantic objects to plain JSON-serializable dict."""
    def default(obj):
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)
    return json.loads(json.dumps(data, default=default))


def new_session(product_name: str, target_price: float = None,
                price_min: float = None, price_max: float = None,
                company: str = "TechSphere") -> str:
    import uuid
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    if target_price is not None and price_min is None:
        price_min = target_price * 0.8
        price_max = target_price * 1.2

    with SessionLocal() as db:
        db.add(SessionRecord(
            session_id=session_id,
            product_name=product_name,
            price_min=price_min,
            price_max=price_max,
            status="running"
        ))
        db.commit()
    return session_id


def save_step(session_id, step, label, data):
    with SessionLocal() as db:
        db.add(StepRecord(
            session_id=session_id,
            step=step,
            label=label,
            data=_to_json(data)   # ← التغيير الوحيد هنا
        ))
        db.commit()


def save_report(session_id, html):
    with SessionLocal() as db:
        db.merge(ReportRecord(session_id=session_id, html=html))
        db.commit()


def finish_session(session_id, total_found=0, in_range_count=0,
                   total_products=None, top_product=None, top_score=0):
    if total_products is not None:
        total_found = total_products
    with SessionLocal() as db:
        rec = db.get(SessionRecord, session_id)
        if rec:
            rec.status = "done"
            rec.total_found = total_found
            rec.in_range_count = in_range_count
            rec.finished_at = datetime.now()
            db.commit()


def fail_session(session_id, error):
    with SessionLocal() as db:
        rec = db.get(SessionRecord, session_id)
        if rec:
            rec.status = "failed"
            rec.error = error
            rec.finished_at = datetime.now()
            db.commit()


def list_sessions(limit=50):
    with SessionLocal() as db:
        rows = db.query(SessionRecord).order_by(
            SessionRecord.started_at.desc()
        ).limit(limit).all()
        return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]


def get_session(session_id):
    with SessionLocal() as db:
        r = db.get(SessionRecord, session_id)
        if not r:
            return None
        return {c.name: getattr(r, c.name) for c in r.__table__.columns}


def get_all_steps(session_id):
    with SessionLocal() as db:
        rows = db.query(StepRecord).filter_by(
            session_id=session_id
        ).order_by(StepRecord.step).all()
        return [
            {"step": r.step, "label": r.label, "data": r.data, "saved_at": str(r.saved_at)}
            for r in rows
        ]


def get_step(session_id, step_number):
    with SessionLocal() as db:
        r = db.query(StepRecord).filter_by(
            session_id=session_id, step=step_number
        ).first()
        if not r:
            return None
        return {"step": r.step, "label": r.label, "data": r.data, "saved_at": str(r.saved_at)}


def get_report_path(session_id):
    return get_report_html(session_id)


def get_report_html(session_id):
    with SessionLocal() as db:
        r = db.get(ReportRecord, session_id)
        return r.html if r else None


def get_stats():
    with SessionLocal() as db:
        from sqlalchemy import func
        total    = db.query(func.count(SessionRecord.session_id)).scalar()
        done     = db.query(func.count(SessionRecord.session_id)).filter_by(status="done").scalar()
        failed   = db.query(func.count(SessionRecord.session_id)).filter_by(status="failed").scalar()
        running  = db.query(func.count(SessionRecord.session_id)).filter_by(status="running").scalar()
        total_products = db.query(func.coalesce(func.sum(SessionRecord.total_found), 0)).scalar()
        return {
            "total_searches": total,
            "completed":      done,
            "failed":         failed,
            "running":        running,
            "total_products": total_products,
        }