from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(code="not_found", message=message, status_code=404, details=details)


class ConflictError(AppError):
    def __init__(
        self,
        code: str = "conflict",
        message: str = "Conflict occurred",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(code=code, message=message, status_code=409, details=details)


class BadRequestError(AppError):
    def __init__(
        self,
        code: str = "bad_request",
        message: str = "Bad request",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(code=code, message=message, status_code=400, details=details)


class PayloadTooLargeError(AppError):
    def __init__(
        self,
        message: str = "Payload too large",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code="payload_too_large",
            message=message,
            status_code=413,
            details=details,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
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
