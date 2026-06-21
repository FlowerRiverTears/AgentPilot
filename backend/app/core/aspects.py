"""Cross-cutting concerns middleware: logging, tracing, timing."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agentpilot.request")


class AspectMiddleware(BaseHTTPMiddleware):
    """Middleware for cross-cutting concerns: request logging, tracing, timing.

    Future: rate limiting, request ID propagation.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health checks from verbose logging
        is_health = request.url.path in ("/health", "/health/stats")

        # Generate trace ID
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex[:12])

        start_time = time.time()

        # Process request
        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Add trace ID to response
        response.headers["X-Trace-Id"] = trace_id

        # Log request (skip health checks unless slow)
        if not is_health or duration_ms > 1000:
            logger.info(
                "%s %s → %d (%.0fms) trace=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                trace_id,
            )

        # Log slow requests as warnings
        if duration_ms > 5000:
            logger.warning(
                "Slow request: %s %s (%.0fms) trace=%s",
                request.method,
                request.url.path,
                duration_ms,
                trace_id,
            )

        return response
