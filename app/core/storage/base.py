import uuid
from typing import Protocol

# 명세서 5번: jpg·png만 허용
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
}

KEY_PREFIX = "prescriptions"


def build_image_key(child_id: int, content_type: str) -> str:
    """prescriptions/{child_id}/{무작위값}.{확장자} 형태의 저장 키를 만든다."""
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if extension is None:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {content_type}")
    return f"{KEY_PREFIX}/{child_id}/{uuid.uuid4().hex}.{extension}"


class ImageStorage(Protocol):
    def upload_image(self, child_id: int, data: bytes, content_type: str) -> str:
        """이미지를 저장하고 저장 키를 돌려준다."""
        ...

    def get_image(self, key: str) -> bytes:
        """저장된 이미지를 바이트로 읽는다. 없으면 FileNotFoundError."""
        ...

    def get_presigned_url(self, key: str, expires_in: int | None = None) -> str:
        """잠깐만 쓸 수 있는 조회 주소를 돌려준다. expires_in을 주지 않으면 설정값(기본 600초)."""
        ...

    def delete_image(self, key: str) -> None:
        """이미지를 지운다. 이미 없어도 오류를 내지 않는다."""
        ...
