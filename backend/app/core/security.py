from fastapi import Header, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
esp32_key_header = APIKeyHeader(name="X-ESP32-Key", auto_error=False)


async def verify_api_key(x_api_key: str = Security(api_key_header)):
    """
    Validates the caller's API key.
    Required for secure administrative and AI pipeline endpoints.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required API key header (X-API-Key)",
        )
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or unauthorized API key",
        )
    return x_api_key


async def verify_esp32_key(x_esp32_key: str = Security(esp32_key_header)):
    """
    Validates ESP32 hardware authentication token.
    """
    if not x_esp32_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ESP32 hardware security key (X-ESP32-Key)",
        )
    if x_esp32_key != settings.ESP32_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized ESP32 device token",
        )
    return x_esp32_key
