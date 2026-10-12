"""Signed access/refresh token pairs (port of shared/authentication/JWTAuthentication.go)."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """The token is malformed, forged, expired or of the wrong type."""


@dataclass(frozen=True, slots=True)
class TokenPair:
    access: str
    refresh: str
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: int
    expires_at: datetime


class JWTAuthentication:
    _ALGORITHM = "HS256"
    _REQUIRED_CLAIMS = ("sub", "type", "iss", "aud", "iat", "nbf", "exp", "jti")

    def __init__(
        self,
        secret_key: str,
        issuer: str,
        access_expires: timedelta,
        refresh_expires: timedelta,
    ) -> None:
        self._secret_key = secret_key
        self._issuer = issuer
        self._access_expires = access_expires
        self._refresh_expires = refresh_expires

    def create_token_pair(
        self, user_id: int, refresh_expires_at: datetime | None = None
    ) -> TokenPair:
        """Issue a pair; pass ``refresh_expires_at`` on rotation to keep the session's lifetime.

        The access token never outlives the refresh token.
        """
        now = datetime.now(UTC).replace(microsecond=0)  # JWT dates have second precision
        refresh_expires_at = refresh_expires_at or now + self._refresh_expires
        access_expires_at = min(now + self._access_expires, refresh_expires_at)
        return TokenPair(
            access=self._sign(user_id, TokenType.ACCESS, now, access_expires_at),
            refresh=self._sign(user_id, TokenType.REFRESH, now, refresh_expires_at),
            refresh_expires_at=refresh_expires_at,
        )

    def parse_token(self, token: str, token_type: TokenType) -> TokenClaims:
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._ALGORITHM],
                audience=self._issuer,
                issuer=self._issuer,
                options={"require": list(self._REQUIRED_CLAIMS)},
            )
        except jwt.ExpiredSignatureError as error:
            raise TokenError("token has expired") from error
        except jwt.InvalidTokenError as error:
            raise TokenError("token is invalid") from error
        if claims["type"] != token_type:
            raise TokenError("token is invalid")
        return TokenClaims(
            user_id=int(claims["sub"]),
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )

    def _sign(
        self, user_id: int, token_type: TokenType, issued_at: datetime, expires_at: datetime
    ) -> str:
        claims = {
            "sub": str(user_id),
            "type": token_type.value,
            "iss": self._issuer,
            "aud": self._issuer,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expires_at,
            "jti": secrets.token_hex(16),  # makes every token unique, even within one second
        }
        return jwt.encode(claims, self._secret_key, algorithm=self._ALGORITHM)
