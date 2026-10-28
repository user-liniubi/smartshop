from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.exceptions import AppError
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.models import UserRole
from backend.app.repositories.users import get_user_by_username
from backend.app.schemas.auth import LoginRequest, LoginResponse, UserResponse

DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def login(self, credentials: LoginRequest) -> LoginResponse:
        user = get_user_by_username(self.session, credentials.username)
        encoded_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_matches = verify_password(credentials.password, encoded_hash)
        if user is None or not password_matches:
            raise AppError(
                status_code=401,
                code="invalid_credentials",
                message="用户名或密码错误",
            )

        token = create_access_token(
            user_id=user.id,
            role=user.role,
            secret=self.settings.auth_secret,
            expires_minutes=self.settings.auth_token_expire_minutes,
        )
        return LoginResponse(
            access_token=token,
            expires_in=self.settings.auth_token_expire_minutes * 60,
            user=UserResponse(
                id=user.id,
                username=user.username,
                role=UserRole(user.role),
            ),
        )
