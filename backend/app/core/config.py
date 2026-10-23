from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
#giúp tìm env khi chạy từ các thư mục khác
#Pydantic tự chuyển tên chữ hoa trong environment thành tên field chữ thường.
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    log_level: Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
] = "INFO"
    max_chunk_characters: int = Field(
    default=1200,
    ge=200,
)
    embedding_dimensions: int = Field(
    default=1536,
    gt=0,
)

    embedding_batch_size: int = Field(
    default=64,
    gt=0,
    le=2048,
)
#SecrectStr giúp ngăn print ra key env 
    openai_api_key: SecretStr
    qdrant_cloud_url: str
    qdrant_cloud_api_key: SecretStr

    qdrant_collection_name: str = Field(
    default="ucp600_dense_v1",
    min_length=1,
)
    
    database_url: SecretStr

    minio_endpoint: str | None = None
    minio_access_key: SecretStr | None = None
    minio_secret_key: SecretStr | None = None
    minio_bucket: str = Field(
        min_length=3,
        max_length=63,
    )
    minio_secure: bool


    default_llm_model: str = "gpt-4o-mini"
    default_embedding_model: str = "text-embedding-3-small"

    max_retry_count: int = Field(default=2, ge=0)
    top_k_per_branch: int = Field(default=20, gt=0)
    final_top_n: int = Field(default=5, gt=0)

    @model_validator(mode="after")
    def validate_retrieval_limits(self) -> "Settings":
        """Ensure the final result count does not exceed retrieved candidates."""
        if self.final_top_n > self.top_k_per_branch:
            raise ValueError(
                "FINAL_TOP_N must be less than or equal to TOP_K_PER_BRANCH"
            )

    



        return self
# ném ra lỗi khi final top > top k ví dụ top k 3 mà final yêu cầu 5 thì sẽ ném ra lỗi 
        


    
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
# đọc và lưu cấu hình 1 lần, khi dùng thì lấy ra tránh bị gọi nhiều lần


# viết lại constant