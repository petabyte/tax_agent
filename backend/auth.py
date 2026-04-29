import os
from fastapi import Header, HTTPException


def require_api_key(x_api_key: str = Header(...)) -> str:
    valid_keys = {k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()}
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
