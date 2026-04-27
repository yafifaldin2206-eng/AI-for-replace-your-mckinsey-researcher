"""Clerk JWT verification for FastAPI."""
from typing import Annotated
from fastapi import Depends, HTTPException, Header, status
import httpx
from jose import jwt, JWTError
from functools import lru_cache
import structlog

from app.config import settings

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_jwks_url() -> str:
    """Clerk JWKS URL derived from the issuer."""
    return f"{settings.CLERK_ISSUER}/.well-known/jwks.json"


_jwks_cache: dict | None = None


async def get_jwks() -> dict:
    """Fetch JWKS from Clerk. Cached in memory."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(get_jwks_url())
            response.raise_for_status()
            _jwks_cache = response.json()
    return _jwks_cache


async def verify_clerk_token(authorization: Annotated[str | None, Header()] = None) -> dict:
    """
    Verify Clerk JWT from the Authorization header.
    Returns decoded claims (user_id is in 'sub').

    In development mode with no token present, returns a mock user.
    """
    if settings.APP_ENV == "development" and not authorization:
        return {"sub": "dev_user_local", "email": "dev@local"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Unknown signing key")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER,
            options={"verify_aud": False},
        )
        return claims

    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


CurrentUser = Annotated[dict, Depends(verify_clerk_token)]


def get_user_id(claims: dict) -> str:
    """Extract user_id from JWT claims."""
    return claims["sub"]
