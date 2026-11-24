"""
Application configuration for the Socratic AI Tutor backend.

All settings are loaded from environment variables (or a local .env file via
python-dotenv). No secrets are hardcoded here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Holds runtime configuration loaded from the environment."""

    # Database configuration
    # Default to a local SQLite file so the app works out-of-the-box for
    # development. Override via the DATABASE_URL environment variable.
    database_url: str = "sqlite:///./socratic_tutor.db"

    # Ollama configuration (local AI model)
    # OLLAMA_BASE_URL points to the running Ollama server.
    # OLLAMA_MODEL is the model name to use (e.g. qwen2.5:7b).
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Secret key used for signing tokens (JWT, cookies, etc.).
    # MUST be provided via the SECRET_KEY environment variable in production.
    secret_key: str = ""

    # File upload configuration
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 20

    # Pydantic-settings configuration: read from a .env file if present.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown environment variables
    )


# Singleton settings instance used across the backend.
settings = Settings()