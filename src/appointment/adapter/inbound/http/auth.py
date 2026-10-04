"""JWT RS256 verification (norm 5.3.7).

Every service validates the token itself. The algorithm is fixed to
RS256; `none` and `HS256` are rejected before signature verification.
"""

from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status

from appointment.config.settings import get_settings

CLOCK_SKEW = timedelta(seconds=30)
ALLOWED_ALGORITHMS = ["RS256"]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: str
    role: str


@lru_cache
def _public_key_pem() -> str:
    pem = get_settings().jwt_public_key
    if not pem:
        raise RuntimeError("JWT_PUBLIC_KEY is not configured")
    return pem.replace("\\n", "\n")


def _decode(token: str) -> dict[str, object]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed token",
        ) from err

    alg = header.get("alg")
    if alg not in ALLOWED_ALGORITHMS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="algorithm not allowed",
        )

    try:
        return jwt.decode(
            token,
            _public_key_pem(),
            algorithms=ALLOWED_ALGORITHMS,
            options={
                "require": ["exp", "sub"],
                "leeway": int(CLOCK_SKEW.total_seconds()),
            },
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
        ) from err
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        ) from err


async def current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or malformed Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    claims = _decode(token)
    role = claims.get("role")
    if not isinstance(role, str) or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing role claim",
        )
    return AuthenticatedUser(user_id=str(claims["sub"]), role=role)


def require_roles(*allowed: str):
    async def _checker(
        user: AuthenticatedUser = Depends(current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient permissions",
            )
        return user

    return _checker
