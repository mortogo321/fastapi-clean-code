"""Registration and token-based authentication (port of usecases/user/userUsecase.go)."""

from app.domain.entities.user import (
    AuthenticatedUser,
    UserEntity,
    UserLoginRequest,
    UserLoginResponse,
    UserRefreshTokenRequest,
    UserRegisterRequest,
    UserTokenEntity,
)
from app.domain.errors import InvalidCredentialsError, InvalidTokenError
from app.domain.repositories.user import IUserRepository
from app.shared.authentication.jwt import JWTAuthentication, TokenClaims, TokenError, TokenType
from app.shared.authentication.password import PasswordHasher


class UserUsecase:
    def __init__(
        self,
        user_repository: IUserRepository,
        jwt_authentication: JWTAuthentication,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._jwt_authentication = jwt_authentication
        self._password_hasher = password_hasher

    async def register_user(self, request: UserRegisterRequest) -> UserEntity:
        password_hash = await self._password_hasher.hash(request.password)
        return await self._user_repository.insert_user(request, password_hash)

    async def user_login(self, request: UserLoginRequest) -> UserLoginResponse:
        user = await self._user_repository.get_user_by_email(request.email)
        password_matches = await self._password_hasher.verify(
            request.password, user.password_hash if user else None
        )
        if user is None or not password_matches:
            raise InvalidCredentialsError

        token_pair = self._jwt_authentication.create_token_pair(user.id)
        token = UserTokenEntity(access=token_pair.access, refresh=token_pair.refresh)
        await self._user_repository.insert_oauth(user.id, token, token_pair.refresh_expires_at)
        return UserLoginResponse(user=user.to_entity(), token=token)

    async def user_refresh_token(self, request: UserRefreshTokenRequest) -> UserLoginResponse:
        """Rotate the session: the presented refresh token (and its access token) stop working."""
        claims = self._parse_token(request.refresh_token, TokenType.REFRESH)
        token_pair = self._jwt_authentication.create_token_pair(
            claims.user_id, refresh_expires_at=claims.expires_at
        )
        token = UserTokenEntity(access=token_pair.access, refresh=token_pair.refresh)
        user = await self._user_repository.rotate_oauth(
            claims.user_id, request.refresh_token, token
        )
        if user is None:
            raise InvalidTokenError("token has been revoked")
        return UserLoginResponse(user=user.to_entity(), token=token)

    async def user_logout(self, request: UserRefreshTokenRequest) -> None:
        claims = self._parse_token(request.refresh_token, TokenType.REFRESH)
        if not await self._user_repository.delete_oauth(claims.user_id, request.refresh_token):
            raise InvalidTokenError("token has been revoked")

    async def user_authentication(self, access_token: str) -> AuthenticatedUser:
        claims = self._parse_token(access_token, TokenType.ACCESS)
        user = await self._user_repository.get_user_by_access_token(claims.user_id, access_token)
        if user is None:
            raise InvalidTokenError("token has been revoked")
        permission = await self._user_repository.get_user_permission_by_user_id(user.id)
        return AuthenticatedUser(
            user=user.to_entity(), permission=permission.permission if permission else None
        )

    def _parse_token(self, token: str, token_type: TokenType) -> TokenClaims:
        try:
            return self._jwt_authentication.parse_token(token, token_type)
        except TokenError as error:
            raise InvalidTokenError(str(error)) from error
