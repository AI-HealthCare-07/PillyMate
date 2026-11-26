"""처방 확정(S-04) → 가이드 생성(S-05) 흐름의 규칙. API 명세서 v1.0 7·8·9번.

PUT  /prescriptions/{id}/confirm  보호자가 OCR 결과를 고쳐서 확정한다     → 상태 CONFIRMED
POST /prescriptions/{id}/guide    확정된 처방으로 가이드를 만든다(약 20초)  → 상태 GUIDE_DONE
GET  /prescriptions/{id}/guide    저장된 가이드를 돌려준다

규칙 검사와 에러 문구 (명세서 문구 그대로)
"""

import logging
from decimal import Decimal
from typing import Any

import anyio
from fastapi import HTTPException, status
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.dtos.prescriptions import (
    GuideResponse,
    MedicationConfirmItem,
    MedicationResponse,
    PrescriptionConfirmRequest,
    PrescriptionDetailResponse,
)
from app.models.children import Child
from app.models.guides import Guide
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.guide.service import generate_guide
from app.services.guide.view import to_view

logger = logging.getLogger(__name__)

GUIDE_TIMEOUT_SECONDS = 60
HTTP_422 = 422  # starlette 버전마다 상수 이름이 달라 숫자로 쓴다
# is_user_edited를 계산할 때 OCR 값(ocr_value_snapshot)과 비교하는 칸
COMPARED_FIELDS = [
    "name",
    "dose_per_time",
    "unit",
    "daily_count",
    "total_days",
    "as_needed",
    "max_daily_count",
    "usage",
    "route",
    "dosage_form",
]

MSG_NOT_FOUND = "처방전을 찾을 수 없어요."
MSG_LOCKED = "가이드를 만든 처방은 수정할 수 없어요."
MSG_NO_MED = "약을 1개 이상 입력해 주세요."
MSG_AS_NEEDED = "필요할 때 먹는 약은 하루 복용 횟수를 비워 주세요."
MSG_UNKNOWN_MED = "이 처방에 없는 약이 포함돼 있어요."
MSG_NOT_CONFIRMED = "처방을 먼저 확정해 주세요."
MSG_GUIDE_FAILED = "가이드를 만들지 못했어요. 다시 시도해 주세요."
MSG_NO_GUIDE = "아직 만든 가이드가 없어요."


def _same(a: Any, b: Any) -> bool:
    """OCR 값과 확정 값이 같은지. 숫자는 4.2와 "4.20"처럼 모양이 달라도 같은 값으로 본다."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except ArithmeticError:
        return str(a).strip() == str(b).strip()


def is_user_edited(snapshot: dict | None, values: dict[str, Any]) -> bool:
    """OCR이 읽은 값과 하나라도 다르면 True. OCR 기록이 없는 약(사용자가 새로 넣은 약)도 True."""
    if not snapshot:
        return True
    return any(not _same(snapshot.get(k), values.get(k)) for k in COMPARED_FIELDS if k in snapshot)


def missing_fields(request: PrescriptionConfirmRequest) -> list[str]:
    """비어 있으면 안 되는 칸 이름 목록 (400 문구에 그대로 넣는다)."""
    missing = []
    if not (request.diagnosis_user_input or "").strip():
        missing.append("diagnosis_user_input")
    for i, m in enumerate(request.medications):
        need = ["name", "dose_per_time", "unit", "route", "dosage_form"]
        # 필요할 때 먹는 약(해열제 등)은 처방전·약봉투에 기간이나 하루 최대 횟수가 없는 경우가 많아
        # total_days·max_daily_count를 비워도 된다. 정해진 때 먹는 약만 하루 횟수·기간이 필수다.
        if not m.as_needed:
            need.extend(["daily_count", "total_days"])
        for key in need:
            value = getattr(m, key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(f"medications[{i}].{key}")
    return missing


def medication_values(m: MedicationConfirmItem) -> dict[str, Any]:
    data = m.model_dump(exclude={"medication_id"})
    data["name"] = (m.name or "").strip()
    return data


def prescription_detail(p: Prescription, meds: list[Medication], has_guide: bool) -> PrescriptionDetailResponse:
    return PrescriptionDetailResponse(
        prescription_id=p.id,
        child_id=p.child_id,  # type: ignore[attr-defined]
        source_type=p.source_type,
        status=p.status,
        prescription_date=p.prescription_date,
        hospital_name=p.hospital_name,
        diagnosis_extracted=p.diagnosis_extracted,
        diagnosis_user_input=p.diagnosis_user_input,
        symptom_notes=p.symptom_notes,
        image_url=None,  # 이미지 주소 발급(서명 URL)은 업로드 API 담당 쪽에서 붙인다
        has_guide=has_guide,
        created_at=p.created_at,
        medications=[
            MedicationResponse(
                medication_id=m.id,
                name=m.name,
                insurance_code=m.insurance_code,
                dose_per_time=float(m.dose_per_time) if m.dose_per_time is not None else None,
                unit=m.unit,
                daily_count=m.daily_count,
                total_days=m.total_days,
                as_needed=m.as_needed,
                max_daily_count=m.max_daily_count,
                usage=m.usage,
                route=m.route,
                dosage_form=m.dosage_form,
                confidence=float(m.confidence) if m.confidence is not None else None,
                is_user_edited=m.is_user_edited,
            )
            for m in meds
        ],
    )


def guide_inputs(child: Child, p: Prescription, meds: list[Medication]) -> tuple[dict, dict, list[dict]]:
    """DB 행 → 가이드 모듈(generate_guide)이 받는 dict 3개."""
    child_d = {
        "birth_date": child.birth_date.isoformat(),
        "weight_kg": float(child.weight_kg) if child.weight_kg is not None else None,
        "allergies": child.allergies,
    }
    prescription_d = {
        "prescription_id": p.id,
        "prescription_date": p.prescription_date.isoformat() if p.prescription_date else None,
        "hospital_name": p.hospital_name,
        "diagnosis_user_input": p.diagnosis_user_input,
        "symptom_notes": p.symptom_notes,
    }
    meds_d = [
        {
            "medication_id": m.id,
            "name": m.name,
            "dose_per_time": float(m.dose_per_time) if m.dose_per_time is not None else None,
            "unit": m.unit,
            "daily_count": m.daily_count,
            "total_days": m.total_days,
            "as_needed": m.as_needed,
            "max_daily_count": m.max_daily_count,
            "usage": m.usage,
            "route": m.route.value if m.route else None,
            "dosage_form": m.dosage_form.value if m.dosage_form else None,
        }
        for m in meds
    ]
    return child_d, prescription_d, meds_d


def guide_response(guide: Guide) -> GuideResponse:
    return GuideResponse(
        guide_id=guide.id,
        prescription_id=guide.prescription_id,  # type: ignore[attr-defined]
        created_at=guide.created_at,
        guide_content=guide.guide_content,  # type: ignore[arg-type]
    )


class PrescriptionService:
    def __init__(self) -> None:
        self.repo = PrescriptionRepository()

    async def _get(self, prescription_id: int, guardian_id: int) -> Prescription:
        p = await self.repo.get_for_guardian(prescription_id, guardian_id)
        if p is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NOT_FOUND)
        return p

    # ------------------------------------------------------------------ 7. 처방 확정
    async def confirm(
        self, prescription_id: int, guardian_id: int, request: PrescriptionConfirmRequest
    ) -> PrescriptionDetailResponse:
        p = await self._get(prescription_id, guardian_id)
        if p.status == PrescriptionStatus.GUIDE_DONE or await self.repo.has_guide(p.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_LOCKED)
        if not request.medications:
            raise HTTPException(status_code=HTTP_422, detail=MSG_NO_MED)
        if any(m.as_needed and m.daily_count is not None for m in request.medications):
            raise HTTPException(status_code=HTTP_422, detail=MSG_AS_NEEDED)
        missing = missing_fields(request)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"필수 항목을 입력해 주세요: {', '.join(missing)}"
            )

        existing = {m.id: m for m in await self.repo.get_medications(p.id)}
        sent_ids = [m.medication_id for m in request.medications if m.medication_id is not None]
        if any(i not in existing for i in sent_ids) or len(sent_ids) != len(set(sent_ids)):
            raise HTTPException(status_code=HTTP_422, detail=MSG_UNKNOWN_MED)

        async with in_transaction():
            await self.repo.update_prescription(
                p,
                {
                    "prescription_date": request.prescription_date or p.prescription_date,
                    "hospital_name": request.hospital_name or p.hospital_name,
                    "diagnosis_user_input": (request.diagnosis_user_input or "").strip(),
                    "symptom_notes": request.symptom_notes,
                    "status": PrescriptionStatus.CONFIRMED,
                },
            )
            for item in request.medications:
                values = medication_values(item)
                if item.medication_id is None:
                    values["is_user_edited"] = True
                    await self.repo.create_medication(p.id, values)
                else:
                    med = existing[item.medication_id]
                    values["is_user_edited"] = is_user_edited(med.ocr_value_snapshot, values)  # type: ignore[arg-type]
                    await self.repo.update_medication(med, values)
            # 확정 목록에서 빠진 약은 보호자가 지운 것
            await self.repo.delete_medications([i for i in existing if i not in sent_ids])

        return prescription_detail(p, await self.repo.get_medications(p.id), has_guide=False)

    # ------------------------------------------------------------------ 8. 가이드 생성
    async def create_guide(self, prescription_id: int, guardian_id: int) -> tuple[GuideResponse, bool]:
        """(가이드, 새로 만들었는지). 이미 있으면 다시 만들지 않고 그대로 돌려준다(LLM 비용 아끼기)."""
        p = await self._get(prescription_id, guardian_id)
        guide = await self.repo.get_guide(p.id)
        if guide:
            return guide_response(guide), False
        if p.status != PrescriptionStatus.CONFIRMED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_NOT_CONFIRMED)

        meds = await self.repo.get_medications(p.id)
        child_d, prescription_d, meds_d = guide_inputs(p.child, p, meds)
        try:
            with anyio.fail_after(GUIDE_TIMEOUT_SECONDS):
                raw = await anyio.to_thread.run_sync(
                    lambda: generate_guide(child_d, prescription_d, meds_d), abandon_on_cancel=True
                )
            content = to_view(raw)
        except Exception as e:  # LLM 실패는 모듈 안에서 fallback으로 처리되므로, 여기 오는 건 예상 못 한 오류
            logger.exception("가이드 생성 실패: prescription_id=%s", p.id)
            # 상태는 CONFIRMED 그대로 둔다 → 보호자가 같은 버튼으로 다시 시도할 수 있다
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=MSG_GUIDE_FAILED) from e

        try:
            async with in_transaction():
                guide = await self.repo.create_guide(p.id, content)
                await self.repo.update_prescription(p, {"status": PrescriptionStatus.GUIDE_DONE})
        except IntegrityError:
            # 버튼을 두 번 눌러 동시에 만들어진 경우: 먼저 저장된 것을 돌려준다
            existing = await self.repo.get_guide(p.id)
            if existing is None:
                raise
            return guide_response(existing), False
        return guide_response(guide), True

    # ------------------------------------------------------------------ 9. 가이드 조회
    async def get_guide(self, prescription_id: int, guardian_id: int) -> GuideResponse:
        p = await self._get(prescription_id, guardian_id)
        guide = await self.repo.get_guide(p.id)
        if guide is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NO_GUIDE)
        return guide_response(guide)
