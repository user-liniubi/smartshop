import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: int
    role: str
    expires_at: int


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """Hash a password using a salted scrypt digest."""

    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符")

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing why a hash is malformed."""

    try:
        algorithm, n, r, p, salt, expected_digest = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(_decode(expected_digest)),
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(digest, _decode(expected_digest))


def create_access_token(
    *,
    user_id: int,
    role: str,
    secret: str,
    expires_minutes: int,
    now: datetime | None = None,
) -> str:
    """Create a compact signed bearer token."""

    current_time = now or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(current_time.timestamp()) + expires_minutes * 60,
    }
    encoded_payload = _encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def decode_access_token(token: str, secret: str) -> AccessTokenClaims:
    """Validate token integrity and expiry, raising ValueError on failure."""

    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        provided_signature = _decode(encoded_signature)
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise ValueError("invalid signature")

        payload = json.loads(_decode(encoded_payload))
        user_id = payload["sub"]
        role = payload["role"]
        expires_at = payload["exp"]
        if (
            not isinstance(user_id, int)
            or not isinstance(role, str)
            or not isinstance(expires_at, int)
            or expires_at <= int(time.time())
        ):
            raise ValueError("invalid payload")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("invalid access token") from None

    return AccessTokenClaims(user_id=user_id, role=role, expires_at=expires_at)
