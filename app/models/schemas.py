from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SearchRequest(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=200, example="standing desk")
    target_price: float = Field(..., gt=0, example=5000.0, description="Target avg price in EGP")
    price_tolerance_pct: float = Field(default=30.0, ge=0, le=100,
                                       description="% above/below target to include")
    company_name: str = Field(default="TechSphere")
    country: str = Field(default="Egypt")
    top_picks: int = Field(default=10, ge=1, le=20)


class ScoreBreakdown(BaseModel):
    price_available: int = 0
    price_competitiveness: int = 0
    price_proximity: int = 0
    description_quality: int = 0
    has_image: int = 0
    clear_title: int = 0
    search_relevance: int = 0


class Product(BaseModel):
    page_url: str
    product_url: str
    product_title: str
    product_image_url: str = ""
    product_current_price: str = "N/A"
    price_numeric: Optional[float] = None
    description: str = ""
    source_title: str = ""
    score: int = 0
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    rank: int = 0
    price_diff_pct: Optional[float] = None


class SearchResult(BaseModel):
    url: str
    title: str
    score: float
    search_query: str
    content: str


class SearchResponse(BaseModel):
    job_id: str                          
    status: str = "completed"
    product_name: str
    target_price: float
    total_found: int
    products: list[Product]
    generated_at: datetime = Field(default_factory=datetime.now)
    report_url: str = ""
    introduction: str = ""
    recommendation: str = ""


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
