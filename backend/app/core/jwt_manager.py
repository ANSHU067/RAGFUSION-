"""JWT creation, verification, rotation and revocation primitives."""

from __future__ import annotations

import hashlib
import secrets
from threading import RLock
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.core.environment import SecurityEnvironment


class TokenValidationError(ValueError):
    """Raised when a bearer token cannot be trusted."""


class JWTManager:
    """Issue and verify audience-bound tokens; inject this service where needed."""

    def __init__(
        self,
        environment: SecurityEnvironment,
        *,
        signing_keys: Mapping[str, str] | None = None,
        verification_keys: Mapping[str, str] | None = None,
        active_key_id: str = "current",
    ) -> None:
        environment.validate()
        self.environment = environment
        default_key = (
            environment.jwt_private_key
            if environment.jwt_algorithm == "RS256"
            else environment.jwt_secret
        )
        self._signing_keys = dict(signing_keys or {active_key_id: default_key or ""})
        if active_key_id not in self._signing_keys:
            raise ValueError("active key id must exist in signing_keys")
        self._active_key_id = active_key_id
        self._verification_keys = dict(
            verification_keys
            or (
                {active_key_id: environment.jwt_public_key or ""}
                if environment.jwt_algorithm == "RS256"
                else self._signing_keys
            )
        )
        if active_key_id not in self._verification_keys:
            raise ValueError("active key id must exist in verification_keys")
        self._revoked: dict[str, datetime] = {}
        self._lock = RLock()

    def issue_access_token(
        self,
        subject: str,
        role: str,
        *,
        expires_in: timedelta = timedelta(minutes=15),
        extra_claims: Mapping[str, Any] | None = None,
    ) -> str:
        return self._issue(
            subject, "access", expires_in, role=role, extra_claims=extra_claims
        )

    def issue_refresh_token(
        self, subject: str, *, expires_in: timedelta = timedelta(days=30)
    ) -> str:
        return self._issue(subject, "refresh", expires_in)

    def _issue(
        self,
        subject: str,
        token_type: str,
        expires_in: timedelta,
        *,
        role: str | None = None,
        extra_claims: Mapping[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        claims: dict[str, Any] = {
            "sub": subject,
            "type": token_type,
            "iat": now,
            "nbf": now,
            "exp": now + expires_in,
            "iss": self.environment.jwt_issuer,
            "aud": self.environment.jwt_audience,
            "jti": secrets.token_urlsafe(24),
        }
        if role is not None:
            claims["role"] = role
        if extra_claims:
            claims.update(extra_claims)
        return jwt.encode(
            claims,
            self._signing_keys[self._active_key_id],
            algorithm=self.environment.jwt_algorithm,
            headers={"kid": self._active_key_id, "typ": "JWT"},
        )

    def verify(
        self, token: str, *, expected_type: str | None = "access"
    ) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            key_id = header.get("kid", self._active_key_id)
            if (
                header.get("alg") != self.environment.jwt_algorithm
                or key_id not in self._verification_keys
            ):
                raise TokenValidationError("untrusted signing key")
            key = self._verification_keys[key_id]
            claims = jwt.decode(
                token,
                key,
                algorithms=[self.environment.jwt_algorithm],
                issuer=self.environment.jwt_issuer,
                audience=self.environment.jwt_audience,
                options={
                    "require_exp": True,
                    "require_iat": True,
                    "require_sub": True,
                    "require_jti": True,
                },
            )
        except (JWTError, KeyError, TypeError) as exc:
            raise TokenValidationError("invalid or expired token") from exc
        if expected_type and claims.get("type") != expected_type:
            raise TokenValidationError("invalid token type")
        jti = claims.get("jti")
        if not isinstance(jti, str) or self._is_revoked(jti):
            raise TokenValidationError("revoked token")
        return claims

    def revoke(self, token: str) -> None:
        """Revoke a verified token synchronously; this never returns a coroutine."""
        claims = self.verify(token, expected_type=None)
        expires = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
        with self._lock:
            self._cleanup_revocations()
            self._revoked[claims["jti"]] = expires

    def rotate_signing_key(
        self,
        key_id: str,
        key: str,
        *,
        verification_key: str | None = None,
        make_active: bool = True,
    ) -> None:
        if not key_id or not key:
            raise ValueError("key id and key are required")
        self._signing_keys[key_id] = key
        self._verification_keys[key_id] = verification_key or key
        if make_active:
            self._active_key_id = key_id

    def _is_revoked(self, jti: str) -> bool:
        self._cleanup_revocations()
        return jti in self._revoked

    def _cleanup_revocations(self) -> None:
        now = datetime.now(timezone.utc)
        for jti, expiry in list(self._revoked.items()):
            if expiry <= now:
                del self._revoked[jti]

    @staticmethod
    def token_fingerprint(token: str) -> str:
        """A safe identifier suitable for security logs; never log the token."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
