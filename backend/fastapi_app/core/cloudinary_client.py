"""One-time Cloudinary SDK configuration (free 25 GB tier).

Call init_cloudinary() before any upload; it returns False when credentials
are missing so callers can fall back to local disk storage.
"""

from functools import lru_cache

from fastapi_app.core.config import get_settings


@lru_cache(maxsize=1)
def init_cloudinary() -> bool:
    settings = get_settings()
    if not settings.cloudinary_configured:
        return False
    import cloudinary

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    return True
