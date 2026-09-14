from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.exceptions import (
    AppError,
    ConflictError,
    InactiveUserError,
    InvalidCredentialsError,
    NotFoundError,
)

_STATUS_BY_ERROR: list[tuple[type[AppError], int]] = [
    (InvalidCredentialsError, status.HTTP_401_UNAUTHORIZED),
    (InactiveUserError, status.HTTP_403_FORBIDDEN),
    (ConflictError, status.HTTP_409_CONFLICT),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
]


def _status_for(exc: AppError) -> int:
    for error_type, code in _STATUS_BY_ERROR:
        if isinstance(exc, error_type):
            return code
    return status.HTTP_400_BAD_REQUEST


def register_exception_handlers(app: FastAPI) -> None:
    """Traduce los errores de negocio a respuestas HTTP consistentes."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if isinstance(exc, InvalidCredentialsError)
            else None
        )
        return JSONResponse(
            status_code=_status_for(exc),
            content={"detail": exc.message},
            headers=headers,
        )
