from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import AppError
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.repositories.users import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=401,
            code="authentication_required",
            message="请先登录",
        )

    try:
        claims = decode_access_token(credentials.credentials, settings.auth_secret)
    except ValueError:
        raise AppError(
            status_code=401,
            code="invalid_token",
            message="登录状态无效或已过期",
        ) from None

    user = get_user_by_id(session, claims.user_id)
    if user is None or user.role != claims.role:
        raise AppError(
            status_code=401,
            code="invalid_token",
            message="登录状态无效或已过期",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
