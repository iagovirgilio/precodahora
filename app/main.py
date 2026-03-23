import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.deps.auth import rate_limit_identity
from app.routers.precos import router as precos_router
from app.schemas.errors import error_json_response, error_payload

_REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_MAX_LEN = 128
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,128}$")


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
_RATE_LIMIT_EXEMPT_PATHS = frozenset(
    {"/health", "/docs", "/redoc", "/openapi.json"}
)


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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in _RATE_LIMIT_EXEMPT_PATHS:
        started = time.time()
        response = await call_next(request)
        elapsed_ms = round((time.time() - started) * 1000, 2)
        rid = _request_id_from_state(request)
        logger.info(
            "http_request method=%s path=%s status=%s elapsed_ms=%s request_id=%s",
            request.method,
            path,
            response.status_code,
            elapsed_ms,
            rid,
        )
        return response

    identity = rate_limit_identity(request)
    now = time.time()
    bucket = _rate_limit_bucket[identity]
    janela = settings.rate_limit_window_seconds
    while bucket and (now - bucket[0]) > janela:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_requests_per_minute:
        rid = _request_id_from_state(request)
        logger.warning("rate_limit_exceeded identity=%s request_id=%s", identity, rid)
        return error_json_response(
            429,
            "rate_limit_exceeded",
            "Limite de requisicoes por minuto excedido.",
            request_id=rid,
        )
    bucket.append(now)
    started = time.time()
    response = await call_next(request)
    elapsed_ms = round((time.time() - started) * 1000, 2)
    rid = _request_id_from_state(request)
    logger.info(
        "http_request method=%s path=%s status=%s elapsed_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        rid,
    )
    return response


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
    }
