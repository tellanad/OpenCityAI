from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OpenCity AI"
    environment: str = "dev"
    log_level: str = "INFO"

    admin_api_key: str = "change-me"

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "opencity"
    vector_size: int = 384

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "phi3:mini"
    ollama_timeout_sec: int = 45

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    retrieval_top_k: int = 8
    similarity_threshold: float = 0.35

    city_config_dir: str = "./cities"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def city_dir(self) -> Path:
        p = Path(self.city_config_dir)
        if p.is_absolute():
            return p
        return (self.project_root / p).resolve()

    @property
    def state_dir(self) -> Path:
        return (self.project_root / "backend" / "data" / "state").resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
