"""Custom exception classes and error handlers."""
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class MarswalkException(Exception):
    """Base exception class for MARSWALK backend."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class InvalidRequestException(MarswalkException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 422):
        super().__init__(
            code="INVALID_REQUEST",
            message=message,
            status_code=status_code,
            details=details,
        )


class NotFoundException(MarswalkException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UpstreamUnavailableException(MarswalkException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 502):
        super().__init__(
            code="UPSTREAM_UNAVAILABLE",
            message=message,
            status_code=status_code,
            details=details,
        )


class InternalErrorException(MarswalkException):
    def __init__(self, message: str = "An internal server error occurred.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


async def marswalk_exception_handler(request: Request, exc: MarswalkException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Formats pydantic validation errors cleanly
    details = {}
    for err in exc.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []))
        details[field_path] = err.get("msg", "Validation error")
        
    first_msg = exc.errors()[0].get("msg", "Invalid request body or parameters") if exc.errors() else "Validation failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": f"Validation error: {first_msg}",
                "details": details,
            }
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_map = {
        400: "INVALID_REQUEST",
        404: "NOT_FOUND",
        422: "INVALID_REQUEST",
        502: "UPSTREAM_UNAVAILABLE",
        503: "UPSTREAM_UNAVAILABLE",
        500: "INTERNAL_ERROR",
    }
    code = code_map.get(exc.status_code, "INTERNAL_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail) if exc.detail else "HTTP error",
                "details": {},
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never expose stack traces in API responses
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": {},
            }
        },
    )
