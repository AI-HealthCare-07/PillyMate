from functools import lru_cache

from app.core import config
from app.core.storage.base import ImageStorage


@lru_cache(maxsize=1)
def get_image_storage() -> ImageStorage:
    if config.STORAGE_BACKEND == "s3":
        from app.core.storage.s3 import S3ImageStorage

        return S3ImageStorage(
            bucket=config.S3_BUCKET,
            region=config.AWS_REGION,
            default_expires_in=config.S3_PRESIGNED_URL_EXPIRE_SECONDS,
        )

    from app.core.storage.local import LocalImageStorage

    return LocalImageStorage(base_dir=config.LOCAL_STORAGE_DIR)


def upload_image(child_id: int, data: bytes, content_type: str) -> str:
    return get_image_storage().upload_image(child_id=child_id, data=data, content_type=content_type)


def get_image(key: str) -> bytes:
    return get_image_storage().get_image(key)


def get_presigned_url(key: str, expires_in: int | None = None) -> str:
    return get_image_storage().get_presigned_url(key, expires_in=expires_in)


def delete_image(key: str) -> None:
    get_image_storage().delete_image(key)
