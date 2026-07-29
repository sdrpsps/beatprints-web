import time
import uuid
import logging

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from beatprints_api.api.errors import error_response

logger = logging.getLogger(__name__)


async def request_context_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    started_at = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(
            "Unhandled error while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        response = error_response(
            status_code=500,
            code=50000,
            message="Internal server error",
        )
    response.headers["X-Request-ID"] = request_id
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.3f}"
    return response
