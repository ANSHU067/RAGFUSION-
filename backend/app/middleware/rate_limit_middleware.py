"""Route-specific, distributed IP quotas enforced before endpoint work."""
from __future__ import annotations

from ipaddress import ip_address, ip_network

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.rate_limiter import RateLimiter, RateLimitPolicy, RateLimitUnavailable


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limiter: RateLimiter | None = None,
                 policies: dict[str, RateLimitPolicy] | None = None,
                 trusted_proxies: tuple[str, ...] = (), api_prefix: str = "/api/v1") -> None:
        super().__init__(app)
        self.limiter = limiter
        self.prefix = api_prefix.rstrip("/")
        self.trusted_proxies = tuple(ip_network(value, strict=False) for value in trusted_proxies)
        self.policies = policies or {
            "auth": RateLimitPolicy(7, 60),
            "chat": RateLimitPolicy(30, 60),
            "ingestion": RateLimitPolicy(10, 60),
            "api": RateLimitPolicy(120, 60),
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/")
        # Keep health reachable during outages; no business work is exempt.
        if request.method == "OPTIONS" or path == self.prefix + "/health":
            return await call_next(request)
        category = self._category(path, request.method)
        limiter = self.limiter if self.limiter is not None else request.app.state.rate_limiter
        try:
            result = await limiter.check(f"{category}:{self._identity(request)}", self.policies[category])
        except RateLimitUnavailable:
            return JSONResponse(
                {"error": {"message": "Service temporarily unavailable"}}, status_code=503,
                headers={"Retry-After": "5"},
            )
        if not result.allowed:
            return JSONResponse(
                {"error": {"message": "Rate limit exceeded"}}, status_code=429,
                headers={"Retry-After": str(result.retry_after), "X-RateLimit-Remaining": "0"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response

    def _category(self, path: str, method: str) -> str:
        relative = path.removeprefix(self.prefix + "/")
        parts = relative.split("/")
        if len(parts) == 2 and parts[0] == "auth" and parts[1] in {"login", "signup", "refresh", "logout"}:
            return "auth"
        if method in {"POST", "PUT", "PATCH"}:
            if parts[0] == "chat":
                return "chat"
            if parts[0] in {"documents", "youtube", "website"}:
                return "ingestion"
        return "api"

    def _trusted(self, host: str) -> bool:
        try:
            address = ip_address(host)
            return any(address in network for network in self.trusted_proxies)
        except ValueError:
            return False

    def _identity(self, request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For", "")
        if not self._trusted(peer) or not forwarded or len(forwarded) > 2048:
            return f"ip:{peer}"
        try:
            chain = [str(ip_address(value.strip())) for value in forwarded.split(",")]
        except ValueError:
            return f"ip:{peer}"
        # Ignore attacker-supplied entries left of the first untrusted hop.
        for hop in reversed(chain):
            if not self._trusted(peer):
                break
            peer = hop
            if not self._trusted(peer):
                break
        return f"ip:{peer}"
