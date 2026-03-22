from fastapi import Header, HTTPException, status
from config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify the API key passed in the X-API-Key header."""
    if x_api_key != settings.ai_service_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key
