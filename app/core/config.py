from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    groq_api_key: str = ""
    tavily_api_key: str = ""
    agentops_api_key: str = ""

    
    score_threshold: float = 0.10
    top_picks: int = 10
    no_keywords: int = 10
    max_results_per_query: int = 10

    default_country: str = "Egypt"
    default_language: str = "English"
    target_sites: List[str] = ["amazon.eg", "jumia.com.eg", "noon.com", "carrefouregypt.com", "extra.com.eg"]

    groq_model: str = "llama-3.1-8b-instant"
    temperature: float = 0.1
    max_tokens: int = 400

    max_retries: int = 5
    wait_secs: int = 25

    search_delay: float = 2.0
    price_search_delay: float = 2.0
    image_search_delay: float = 2.0
    database_url: str = "postgresql://procurement:procurement123@localhost:5432/procurement_db"

    output_dir: str = "./output" 

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8" # Specify the encoding of the .env file 
        case_sensitive = False  # Make environment variable names case-insensitive


@lru_cache() # Cache the settings instance to avoid reloading it multiple times
def get_settings() -> Settings:
    return Settings()