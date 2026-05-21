import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class AspectMiddleware(BaseHTTPMiddleware):
    """Cross-cutting middleware for trace, audit, timing and future rate limits."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        start = time.perf_counter()

        request.state.trace_id = trace_id
        request.state.audit = {
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
        }

        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        response.headers["x-trace-id"] = trace_id
        response.headers["x-elapsed-ms"] = str(elapsed_ms)
        return response
