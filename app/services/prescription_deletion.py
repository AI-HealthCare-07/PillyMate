"""명세 9절 처방 이력 삭제 (요구사항 MED-002).

소유권 확인은 라우터의 MyPrescription 의존성이 한다 (남의 처방전은 404).
약·가이드·복약 알림은 DB의 ON DELETE CASCADE로 함께 지워진다.
"""

import logging

from starlette.concurrency import run_in_threadpool

from app.core.storage import delete_image
from app.models.prescriptions import Prescription

logger = logging.getLogger(__name__)


async def delete_prescription(prescription: Prescription) -> None:
    image_key = prescription.image_storage_key
    await prescription.delete()

    # 처방 행을 먼저 지운 뒤 사진을 지운다. 사진 삭제가 실패해도 S3 Lifecycle Rule이 7일 뒤 지운다.
    if image_key:
        try:
            await run_in_threadpool(delete_image, image_key)
        except Exception:
            logger.exception("처방 사진 삭제 실패 (key=%s)", image_key)
