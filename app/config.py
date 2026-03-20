from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Preco da Hora API"
    app_version: str = "1.0.0"
    app_description: str = (
        "API para buscar os 5 menores precos de produtos no Preco da Hora Bahia."
    )
    base_url: str = "https://precodahora.ba.gov.br/produtos/"
    default_latitude: float = -12.2690245
    default_longitude: float = -38.9295865
    default_raio: int = 15
    default_horas: int = 72
    request_timeout_seconds: float = 20.0
    request_retry_attempts: int = 3
    request_backoff_base_seconds: float = 0.5
    cache_ttl_seconds: int = 900
    rate_limit_requests_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PRECODAHORA_",
        extra="ignore",
    )


settings = Settings()
