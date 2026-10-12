from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from app.shared.authentication.jwt import JWTAuthentication, TokenError, TokenType

SECRET = "s" * 32
ISSUER = "test-issuer"


def make_auth(
    secret: str = SECRET, access: int = 900, refresh: int = 3600, issuer: str = ISSUER
) -> JWTAuthentication:
    return JWTAuthentication(secret, issuer, timedelta(seconds=access), timedelta(seconds=refresh))


def claims_for(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0)
    claims: dict[str, Any] = {
        "sub": "7",
        "type": "access",
        "iss": ISSUER,
        "aud": ISSUER,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "jti": "abc",
    }
    claims.update(overrides)
    return {key: value for key, value in claims.items() if value is not None}


def test_round_trip() -> None:
    auth = make_auth()
    pair = auth.create_token_pair(42)
    access = auth.parse_token(pair.access, TokenType.ACCESS)
    refresh = auth.parse_token(pair.refresh, TokenType.REFRESH)
    assert access.user_id == 42
    assert refresh.user_id == 42
    assert refresh.expires_at == pair.refresh_expires_at
    assert access.expires_at < refresh.expires_at


def test_wrong_type_is_rejected() -> None:
    auth = make_auth()
    pair = auth.create_token_pair(1)
    with pytest.raises(TokenError, match="token is invalid"):
        auth.parse_token(pair.access, TokenType.REFRESH)
    with pytest.raises(TokenError, match="token is invalid"):
        auth.parse_token(pair.refresh, TokenType.ACCESS)


def test_expired_token() -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        claims_for(iat=past - timedelta(hours=1), nbf=past - timedelta(hours=1), exp=past),
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(TokenError, match="token has expired"):
        make_auth().parse_token(token, TokenType.ACCESS)


def test_tampered_signature() -> None:
    auth = make_auth()
    token = auth.create_token_pair(1).access
    head, payload, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(TokenError, match="token is invalid"):
        auth.parse_token(f"{head}.{payload}.{flipped}", TokenType.ACCESS)


def test_tampered_payload() -> None:
    auth = make_auth()
    other = auth.create_token_pair(2).access.split(".")[1]
    head, _, signature = auth.create_token_pair(1).access.split(".")
    with pytest.raises(TokenError, match="token is invalid"):
        auth.parse_token(f"{head}.{other}.{signature}", TokenType.ACCESS)


def test_wrong_secret() -> None:
    token = make_auth(secret="t" * 32).create_token_pair(1).access
    with pytest.raises(TokenError, match="token is invalid"):
        make_auth().parse_token(token, TokenType.ACCESS)


@pytest.mark.parametrize("claim", ["iss", "aud"])
def test_wrong_issuer_or_audience(claim: str) -> None:
    token = jwt.encode(claims_for(**{claim: "someone-else"}), SECRET, algorithm="HS256")
    with pytest.raises(TokenError, match="token is invalid"):
        make_auth().parse_token(token, TokenType.ACCESS)


def test_alg_none_is_rejected() -> None:
    token = jwt.encode(claims_for(), None, algorithm="none")
    with pytest.raises(TokenError, match="token is invalid"):
        make_auth().parse_token(token, TokenType.ACCESS)


@pytest.mark.parametrize("claim", ["sub", "type", "iss", "aud", "iat", "nbf", "exp", "jti"])
def test_missing_required_claim(claim: str) -> None:
    token = jwt.encode(claims_for(**{claim: None}), SECRET, algorithm="HS256")
    with pytest.raises(TokenError, match="token is invalid"):
        make_auth().parse_token(token, TokenType.ACCESS)


def test_garbage_token() -> None:
    with pytest.raises(TokenError, match="token is invalid"):
        make_auth().parse_token("not-a-jwt", TokenType.ACCESS)


def test_access_expiry_is_capped_at_refresh_expiry() -> None:
    auth = make_auth(access=3600, refresh=60)
    pair = auth.create_token_pair(1)
    access = auth.parse_token(pair.access, TokenType.ACCESS)
    assert access.expires_at == pair.refresh_expires_at


def test_rotation_keeps_refresh_expiry() -> None:
    auth = make_auth()
    first = auth.create_token_pair(1)
    rotated = auth.create_token_pair(1, refresh_expires_at=first.refresh_expires_at)
    assert rotated.refresh_expires_at == first.refresh_expires_at
    claims = auth.parse_token(rotated.refresh, TokenType.REFRESH)
    assert claims.expires_at == first.refresh_expires_at


def test_pairs_minted_in_the_same_second_differ() -> None:
    auth = make_auth()
    first = auth.create_token_pair(1, refresh_expires_at=datetime.now(UTC) + timedelta(hours=1))
    second = auth.create_token_pair(1, refresh_expires_at=first.refresh_expires_at)
    assert first.access != second.access
    assert first.refresh != second.refresh
