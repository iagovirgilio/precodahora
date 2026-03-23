import hashlib
import hmac

from fastapi import HTTPException, Request

from app.config import settings


def parsed_api_keys() -> frozenset[str]:
    raw = settings.api_keys.strip()
    if not raw:
        return frozenset()
    return frozenset(k.strip() for k in raw.split(",") if k.strip())


def extract_bearer_or_api_key(request: Request) -> str | None:
    x = request.headers.get("x-api-key")
    if x and x.strip():
        return x.strip()
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def keys_match(provided: str, keys: frozenset[str]) -> bool:
    for k in keys:
        if len(provided) == len(k) and hmac.compare_digest(provided, k):
            return True
    return False


def require_api_key(request: Request) -> None:
    if not settings.api_auth_enabled:
        return
    keys = parsed_api_keys()
    if not keys:
        raise HTTPException(
            status_code=503,
            detail="Chaves de API nao configuradas.",
        )
    token = extract_bearer_or_api_key(request)
    if not token or not keys_match(token, keys):
        raise HTTPException(
            status_code=401,
            detail="Chave de API invalida ou ausente.",
        )


def rate_limit_identity(request: Request) -> str:
    token = extract_bearer_or_api_key(request)
    if token:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
        return f"key:{digest}"
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"
