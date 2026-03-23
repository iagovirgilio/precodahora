from typing import Any

from fastapi.responses import JSONResponse


def error_payload(
    code: str,
    message: str,
    request_id: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if request_id:
        err["request_id"] = request_id
    if details is not None:
        err["details"] = details
    return {"error": err}


def error_json_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = error_payload(code, message, request_id=request_id, details=details)
    return JSONResponse(status_code=status_code, content=body)
