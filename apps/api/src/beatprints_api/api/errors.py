import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from beatprints_api.exceptions import AppError
from beatprints_api.models import ApiResponse

logger = logging.getLogger(__name__)


def error_response(
    *,
    status_code: int,
    code: int,
    message: str,
    data: object = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ApiResponse[object](code=code, data=data, message=message)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            status_code=422,
            code=42200,
            message="Request validation failed",
            data={"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP request failed"
        data = None if isinstance(exc.detail, str) else {"detail": exc.detail}
        return error_response(
            status_code=exc.status_code,
            code=exc.status_code * 100,
            message=message,
            data=data,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return error_response(
            status_code=500,
            code=50000,
            message="Internal server error",
        )
