from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://ascent:ascent@localhost:5432/ascent"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # one week
    cors_origins: list[str] = ["http://localhost:3000"]

    # Video storage. "local" writes under media_root; "s3" is reserved for prod.
    storage_backend: str = "local"
    media_root: str = "media"  # relative to the backend working directory
    max_upload_mb: int = 200
    allowed_video_types: list[str] = [
        "video/mp4",
        "video/quicktime",  # .mov
        "video/webm",
        "video/x-matroska",  # .mkv
    ]


settings = Settings()
