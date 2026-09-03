import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("bugflow.errors")


def utc_iso_now() -> str:
    """Return ISO format UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── Error Response Schemas ───────────────────────────────────────────────────

class ValidationErrorDetail(BaseModel):
    loc: list[str | int] = Field(..., description="Location of the validation error")
    msg: str = Field(..., description="Error message for the specific field")
    type: str = Field(..., description="Error type identifier")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable error description")
    error_code: str = Field("ERROR", description="Machine-readable application error code")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(default_factory=utc_iso_now, description="UTC timestamp of error")
    errors: list[ValidationErrorDetail] | None = Field(default=None, description="Optional detailed validation errors")


# ── Custom Application Exception Hierarchy ───────────────────────────────────

class AppException(Exception):
    """Base application exception with error code and status code."""
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(detail)


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND, error_code=error_code)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Authentication required", error_code: str = "UNAUTHORIZED"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED, error_code=error_code)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Access forbidden", error_code: str = "FORBIDDEN"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN, error_code=error_code)


class BadRequestError(AppException):
    def __init__(self, detail: str = "Invalid request payload or parameters", error_code: str = "BAD_REQUEST"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST, error_code=error_code)


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource conflict", error_code: str = "CONFLICT"):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT, error_code=error_code)


# ── Exception Handlers ────────────────────────────────────────────────────────

def format_error_response(
    detail: str,
    status_code: int,
    error_code: str = "ERROR",
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    content = {
        "detail": detail,
        "error_code": error_code,
        "status_code": status_code,
        "timestamp": utc_iso_now(),
    }
    if errors:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content)


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return format_error_response(
        detail=exc.detail,
        status_code=exc.status_code,
        error_code=exc.error_code,
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = "BAD_REQUEST"
    elif exc.status_code == status.HTTP_409_CONFLICT:
        error_code = "CONFLICT"

    headers = getattr(exc, "headers", None)
    response = format_error_response(
        detail=detail_str,
        status_code=exc.status_code,
        error_code=error_code,
    )
    if headers:
        for k, v in headers.items():
            response.headers[k] = v
    return response


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors: list[dict[str, Any]] = []
    error_summaries: list[str] = []

    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", [])]
        field_name = loc[-1] if loc else "field"
        msg = err.get("msg", "Invalid value")
        err_type = err.get("type", "value_error")

        errors.append({
            "loc": err.get("loc", []),
            "msg": msg,
            "type": err_type,
        })
        error_summaries.append(f"Field '{field_name}': {msg}")

    summary_msg = "; ".join(error_summaries) if error_summaries else "Request validation failed"
    return format_error_response(
        detail=summary_msg,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        errors=errors,
    )


async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error occurred: {exc}", exc_info=True)
    return format_error_response(
        detail="A database error occurred while processing your request.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="DATABASE_ERROR",
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return format_error_response(
        detail="An internal server error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
    )
