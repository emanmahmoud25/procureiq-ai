from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.models.database import Base

class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id     = Column(String, primary_key=True)
    product_name   = Column(String)
    price_min      = Column(Float)
    price_max      = Column(Float)
    status         = Column(String, default="running")   # running / done / failed
    total_found    = Column(Integer, default=0)
    in_range_count = Column(Integer, default=0)
    error          = Column(Text, nullable=True)
    started_at     = Column(DateTime, server_default=func.now())
    finished_at    = Column(DateTime, nullable=True)


class StepRecord(Base):
    __tablename__ = "steps"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String)
    step       = Column(Integer)
    label      = Column(String)
    data       = Column(JSON)
    saved_at   = Column(DateTime, server_default=func.now())


class ReportRecord(Base):
    __tablename__ = "reports"

    session_id = Column(String, primary_key=True)
    html       = Column(Text)
    saved_at   = Column(DateTime, server_default=func.now())