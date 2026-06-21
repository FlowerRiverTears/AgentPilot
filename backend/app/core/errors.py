"""Standardized error response models and handlers."""
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    ok: bool = False
    error: dict

    class Config:
        json_schema_extra = {
            "example": {
                "ok": False,
                "error": {"code": "not_found", "message": "Resource not found"}
            }
        }


class ErrorCode:
    """Standard error codes."""
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    VALIDATION = "validation_error"
    RATE_LIMITED = "rate_limited"
    INTERNAL = "internal_error"
    BAD_REQUEST = "bad_request"


def create_error_response(code: str, message: str, status_code: int = 400) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": {"code": code, "message": message}}
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"code": "internal_error", "message": "An unexpected error occurred"}}
    )
