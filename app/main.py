import json
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers.precos import router as precos_router


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%SZ"),
            }
        )


logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())

logger = logging.getLogger("precodahora.api")
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
)

app.include_router(precos_router, prefix="/api/v1")
_rate_limit_bucket: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_limit_bucket[ip]
    janela = 60
    while bucket and (now - bucket[0]) > janela:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_requests_per_minute:
        logger.warning(f"rate_limit_exceeded ip={ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Limite de requisicoes por minuto excedido."},
        )
    bucket.append(now)
    started = time.time()
    response = await call_next(request)
    elapsed_ms = round((time.time() - started) * 1000, 2)
    logger.info(
        f"http_request method={request.method} path={request.url.path} status={response.status_code} elapsed_ms={elapsed_ms}"
    )
    return response


@app.get("/health", tags=["Health"])
def healthcheck() -> dict[str, str | int]:
    return {"status": "ok", "cache_ttl_seconds": settings.cache_ttl_seconds}
