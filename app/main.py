import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from app.config import settings
from app.deps.auth import rate_limit_identity
from app.rate_limiting import try_consume_rate_slot
from app.redis_client import close_redis, get_async_redis, init_redis, redis_ready
from app.routers.precos import router as precos_router
from app.schemas.errors import error_json_response, error_payload

_REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_MAX_LEN = 128
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,128}$")

_RATE_LIMIT_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)

HTTP_REQUESTS_TOTAL = Counter(
    "precodahora_http_requests_total",
    "Total de requisicoes HTTP atendidas",
    ["method", "status_code"],
)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
)

app.include_router(precos_router, prefix="/api/v1")


def _rate_limit_backend_label() -> str:
    if not settings.redis_url.strip():
        return "memory"
    return "redis" if get_async_redis() is not None else "memory"


def _resolve_request_id(request: Request) -> str:
    raw = (request.headers.get(_REQUEST_ID_HEADER) or "").strip()
    if raw and _REQUEST_ID_PATTERN.fullmatch(raw[:_REQUEST_ID_MAX_LEN]):
        return raw[:_REQUEST_ID_MAX_LEN]
    return str(uuid.uuid4())


def _request_id_from_state(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _default_error_code(status_code: int) -> str:
    return {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        429: "rate_limit_exceeded",
        502: "upstream_http_error",
        503: "upstream_network_error",
        500: "internal_error",
    }.get(status_code, "http_error")


def _http_exception_body(request: Request, exc: HTTPException) -> dict:
    rid = _request_id_from_state(request)
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", _default_error_code(exc.status_code)))
        message = str(
            detail.get("message", detail.get("detail", "Erro na requisicao."))
        )
    else:
        code = _default_error_code(exc.status_code)
        message = str(detail)
    return error_payload(code, message, request_id=rid)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    body = _http_exception_body(request, exc)
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    rid = _request_id_from_state(request)
    details = jsonable_encoder(exc.errors())
    return error_json_response(
        422,
        "validation_error",
        "Payload invalido.",
        request_id=rid,
        details=details,
    )


def _observe_request(method: str, status_code: int) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, status_code=str(status_code)).inc()


async def _log_and_observe(
    request: Request, path: str, response: JSONResponse | Response
) -> JSONResponse | Response:
    start = getattr(request.state, "request_start_time", time.time())
    elapsed_ms = round((time.time() - start) * 1000, 2)
    rid = _request_id_from_state(request)
    logger.info(
        "http_request method=%s path=%s status=%s elapsed_ms=%s request_id=%s",
        request.method,
        path,
        response.status_code,
        elapsed_ms,
        rid,
    )
    _observe_request(request.method, response.status_code)
    return response


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    request.state.request_start_time = time.time()
    return await call_next(request)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in _RATE_LIMIT_EXEMPT_PATHS:
        response = await call_next(request)
        return await _log_and_observe(request, path, response)

    identity = rate_limit_identity(request)
    allowed = await try_consume_rate_slot(identity)
    if not allowed:
        rid = _request_id_from_state(request)
        logger.warning("rate_limit_exceeded identity=%s request_id=%s", identity, rid)
        response = error_json_response(
            429,
            "rate_limit_exceeded",
            "Limite de requisicoes por minuto excedido.",
            request_id=rid,
        )
        return await _log_and_observe(request, path, response)

    response = await call_next(request)
    return await _log_and_observe(request, path, response)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = _resolve_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


@app.get("/health", tags=["Health"])
def healthcheck() -> dict[str, str | int]:
    return {
        "status": "ok",
        "cache_ttl_seconds": settings.cache_ttl_seconds,
        "cache_max_entries": settings.cache_max_entries,
        "rate_limit_window_seconds": settings.rate_limit_window_seconds,
        "rate_limit_backend": _rate_limit_backend_label(),
    }


@app.get("/ready", tags=["Health"])
async def readiness() -> JSONResponse:
    redis_ok, redis_status = await redis_ready()
    body: dict[str, object] = {
        "status": "ready" if redis_ok else "not_ready",
        "checks": {"redis": redis_status},
    }
    status_code = 200 if redis_ok else 503
    return JSONResponse(status_code=status_code, content=body)


@app.get("/metrics", tags=["Observabilidade"])
def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
