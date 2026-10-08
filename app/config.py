from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Все значения читаются из переменных окружения / .env."""

    database_url: str = "postgresql+psycopg://confplus_user:123@localhost:5432/confplus"
    test_database_url: str = "postgresql+psycopg://confplus_user:123@localhost:5432/confplus_test"
    secret_key: str = "change-me"  # noqa: S105 — дефолт для разработки, в проде переопределяется через .env
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    debug: bool = True
    host: str = "0.0.0.0"  # noqa: S104 — uvicorn должен принимать внешние подключения
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
