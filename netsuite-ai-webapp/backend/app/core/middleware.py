import hmac
import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response (OWASP best practices)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # CSP: allow self, inline styles/scripts (needed for SPA), Chart.js CDN
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )
        if settings.app_env != "dev":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Protect /admin/* endpoints with a bearer API key."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/admin"):
            # Always require an admin key in non-dev environments
            expected = settings.admin_api_key
            if not expected:
                if settings.app_env != "dev":
                    return JSONResponse(
                        {"detail": "Admin endpoints are disabled (ADMIN_API_KEY not set)"},
                        status_code=503,
                    )
                # In dev mode, allow unauthenticated access if no key is set
                return await call_next(request)

            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return JSONResponse(
                    {"detail": "Missing Authorization header"},
                    status_code=401,
                )
            token = auth.removeprefix("Bearer ").strip()
            if not hmac.compare_digest(token, expected):
                return JSONResponse(
                    {"detail": "Invalid admin API key"},
                    status_code=403,
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter per client IP."""

    def __init__(self, app, rpm: int | None = None):
        super().__init__(app)
        self.rpm = rpm or settings.rate_limit_rpm
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health endpoints
        if request.url.path in ("/healthz", "/readyz"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0  # 1 minute

        # Prune old entries
        timestamps = self._hits[client_ip]
        self._hits[client_ip] = [t for t in timestamps if now - t < window]

        if len(self._hits[client_ip]) >= self.rpm:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": "60"},
            )

        self._hits[client_ip].append(now)
        return await call_next(request)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds a configured maximum."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                {"detail": "Request body too large"},
                status_code=413,
            )
        return await call_next(request)
