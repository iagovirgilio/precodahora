from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Preco da Hora API"
    app_version: str = "1.0.0"
    app_description: str = (
        "API para buscar os 5 menores precos de produtos no Preco da Hora Bahia."
    )
    base_url: str = "https://precodahora.ba.gov.br/produtos/"
    default_latitude: float = -12.2535848
    default_longitude: float = -38.9600762
    default_raio: int = 15
    default_horas: int = 72
    request_timeout_seconds: float = 20.0
    request_retry_attempts: int = 3
    request_backoff_base_seconds: float = 0.5
    cache_ttl_seconds: int = 900
    cache_max_entries: int = 512
    rate_limit_window_seconds: int = 60
    rate_limit_requests_per_minute: int = 60
    api_keys: str = ""
    api_auth_enabled: bool = False
    max_gtins_per_request: int = 50
    redis_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PRECODAHORA_",
        extra="ignore",
    )


settings = Settings()
