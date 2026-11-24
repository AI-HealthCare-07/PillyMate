"""이미지 저장소 유틸 (BE-1 제공, BE-2가 사용).

BE-2는 아래 네 함수만 가져다 쓰면 된다.

    from app.core.storage import upload_image, get_image, get_presigned_url, delete_image

    key = upload_image(child_id=3, data=image_bytes, content_type="image/jpeg")  # 5번 처방전 등록
    url = get_presigned_url(key)                                               # 6번 상세 조회 (10분 유효)
    data = get_image(key)                                                      # 서버에서 원본이 다시 필요할 때 (예: OCR 재시도)
    delete_image(key)                                                          # 5번 OCR 실패, 8번 가이드 생성 후

- 키 규칙: prescriptions/{child_id}/{무작위값}.jpg (png는 .png)
- STORAGE_BACKEND=local(기본)이면 S3 없이 LOCAL_STORAGE_DIR에 저장하므로 AWS 준비 전에도 개발할 수 있다.
- 모두 동기 함수다. async def 안에서 부를 때는 starlette의 run_in_threadpool로 감싼다.
  (명세서 1절 동기 처리 메모: OCR·가이드 API는 def로 작성)
"""

from app.core.storage.base import (
    ALLOWED_CONTENT_TYPES,
    ImageStorage,
    build_image_key,
)
from app.core.storage.factory import (
    delete_image,
    get_image,
    get_image_storage,
    get_presigned_url,
    upload_image,
)

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "ImageStorage",
    "build_image_key",
    "delete_image",
    "get_image",
    "get_image_storage",
    "get_presigned_url",
    "upload_image",
]
