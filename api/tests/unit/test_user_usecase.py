from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.user import (
    UserLoginRequest,
    UserRefreshTokenRequest,
    UserRegisterRequest,
    UserTokenEntity,
)
from app.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.usecases.application import Usecases
from tests.fakes import FakeUserRepository

PASSWORD = "password123"


def register_request(email: str = "ada@example.com") -> UserRegisterRequest:
    return UserRegisterRequest.model_validate(
        {"email": email, "password": PASSWORD, "first_name": "Ada", "last_name": "L"}
    )


def login_request(email: str = "ada@example.com", password: str = PASSWORD) -> UserLoginRequest:
    return UserLoginRequest.model_validate({"email": email, "password": password})


async def test_register_then_duplicate(usecases: Usecases, user_repo: FakeUserRepository) -> None:
    user = await usecases.user.register_user(register_request())
    assert user.email == "ada@example.com"
    assert user_repo.users[user.id].password_hash != PASSWORD
    with pytest.raises(EmailAlreadyRegisteredError):
        await usecases.user.register_user(register_request())


async def test_login_succeeds(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    response = await usecases.user.user_login(login_request())
    assert response.user.email == "ada@example.com"
    authenticated = await usecases.user.user_authentication(response.token.access)
    assert authenticated.user.id == response.user.id
    assert not authenticated.is_admin


async def test_wrong_password_and_unknown_email_are_indistinguishable(
    usecases: Usecases,
) -> None:
    await usecases.user.register_user(register_request())
    with pytest.raises(InvalidCredentialsError) as wrong_password:
        await usecases.user.user_login(login_request(password="wrong-password"))
    with pytest.raises(InvalidCredentialsError) as unknown_email:
        await usecases.user.user_login(login_request(email="nobody@example.com"))
    assert type(wrong_password.value) is type(unknown_email.value)
    assert str(wrong_password.value) == str(unknown_email.value) == "invalid email or password"


async def test_refresh_rotates_the_session(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    first = (await usecases.user.user_login(login_request())).token
    second = (
        await usecases.user.user_refresh_token(UserRefreshTokenRequest(refresh_token=first.refresh))
    ).token

    with pytest.raises(InvalidTokenError):
        await usecases.user.user_refresh_token(UserRefreshTokenRequest(refresh_token=first.refresh))
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_authentication(first.access)

    assert (await usecases.user.user_authentication(second.access)).user.email == "ada@example.com"
    third = await usecases.user.user_refresh_token(
        UserRefreshTokenRequest(refresh_token=second.refresh)
    )
    assert third.token.refresh != second.refresh


async def test_access_token_cannot_be_used_as_refresh(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    token = (await usecases.user.user_login(login_request())).token
    with pytest.raises(InvalidTokenError, match="token is invalid"):
        await usecases.user.user_refresh_token(UserRefreshTokenRequest(refresh_token=token.access))
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_logout(UserRefreshTokenRequest(refresh_token=token.access))


async def test_refresh_token_cannot_authenticate(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    token = (await usecases.user.user_login(login_request())).token
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_authentication(token.refresh)


async def test_logout_revokes_everything(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    token = (await usecases.user.user_login(login_request())).token
    request = UserRefreshTokenRequest(refresh_token=token.refresh)
    await usecases.user.user_logout(request)
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_refresh_token(request)
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_authentication(token.access)
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_logout(request)


async def test_logout_only_ends_one_session(usecases: Usecases) -> None:
    await usecases.user.register_user(register_request())
    first = (await usecases.user.user_login(login_request())).token
    second = (await usecases.user.user_login(login_request())).token
    await usecases.user.user_logout(UserRefreshTokenRequest(refresh_token=first.refresh))
    assert await usecases.user.user_authentication(second.access)


async def test_expired_session_is_rejected(
    usecases: Usecases, user_repo: FakeUserRepository
) -> None:
    user = await usecases.user.register_user(register_request())
    pair = usecases.user._jwt_authentication.create_token_pair(user.id)
    await user_repo.insert_oauth(
        user.id,
        UserTokenEntity(access=pair.access, refresh=pair.refresh),
        datetime.now(UTC) - timedelta(seconds=1),
    )
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_authentication(pair.access)
    with pytest.raises(InvalidTokenError):
        await usecases.user.user_refresh_token(UserRefreshTokenRequest(refresh_token=pair.refresh))


async def test_admin_permission(usecases: Usecases, user_repo: FakeUserRepository) -> None:
    user = await usecases.user.register_user(register_request())
    token = (await usecases.user.user_login(login_request())).token
    assert not (await usecases.user.user_authentication(token.access)).is_admin
    user_repo.grant(user.id, "admin")
    authenticated = await usecases.user.user_authentication(token.access)
    assert authenticated.permission == "admin"
    assert authenticated.is_admin


async def test_other_permission_is_not_admin(
    usecases: Usecases, user_repo: FakeUserRepository
) -> None:
    user = await usecases.user.register_user(register_request())
    user_repo.grant(user.id, "editor")
    token = (await usecases.user.user_login(login_request())).token
    assert not (await usecases.user.user_authentication(token.access)).is_admin
