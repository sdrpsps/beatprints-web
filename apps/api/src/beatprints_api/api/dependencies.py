import secrets
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from beatprints_api.config import settings

bearer = HTTPBearer(
    auto_error=False,
    description="设置 API_KEY 后，在这里填写相同的 Bearer Token。",
)


def require_api_key(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer)
    ] = None,
) -> None:
    if settings.api_key is None:
        return
    if credentials is None or not secrets.compare_digest(
        credentials.credentials, settings.api_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
