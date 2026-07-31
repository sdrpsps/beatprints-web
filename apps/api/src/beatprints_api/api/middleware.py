import logging
import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from beatprints_api.api.errors import error_response
from beatprints_api.config import settings
from beatprints_api.logging import log_event, request_id_context

logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID")
    if supplied and REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return str(uuid.uuid4())


def _should_log_access(request: Request) -> bool:
    return request.url.path.startswith("/v1/")


def _route_name(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def _response_size(response: Response) -> int | None:
    content_length = response.headers.get("Content-Length")
    if content_length is None:
        return None
    try:
        return int(content_length)
    except ValueError:
        return None


async def request_context_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    started_at = time.perf_counter()
    request_id = _request_id(request)
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    try:
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

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms:.0f}"

        if _should_log_access(request):
            log_event(
                logger,
                logging.INFO,
                "http_request",
                "HTTP request completed",
                method=request.method,
                route=_route_name(request),
                status=response.status_code,
                duration_ms=round(elapsed_ms),
                response_bytes=_response_size(response),
                version=settings.build_version,
                git_sha=settings.build_git_sha,
            )
        return response
    finally:
        request_id_context.reset(token)
