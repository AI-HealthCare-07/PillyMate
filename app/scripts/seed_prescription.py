"""개발 DB에 '사진 올리고 OCR까지 끝난' 예시 처방 1건을 넣어요. (확정·가이드 API를 Swagger로 시험해 보는 용도)

실행 (MySQL이 떠 있고 마이그레이션이 끝난 상태에서, 저장소 루트에서):
    uv run --env-file .env python -m app.scripts.seed_prescription --email 내계정@example.com

- 그 이메일로 가입한 계정이 있어야 해요. (먼저 /api/v1/auth/signup 으로 가입)
- 실행할 때마다 예시 아이 1명(없으면 만들고, 있으면 재사용) 밑에 OCR_DONE 처방이 1건씩 새로 생겨요.
- 끝나면 prescription_id와, 확정 API에 그대로 붙여 넣을 JSON을 보여 줘요.
- ENV=prod 에서는 실행되지 않아요.

약 4개는 AI-1이 보내 준 처방전 OCR 예시(해솔소아청소년과의원, 2026-11-12)를 그대로 옮긴 것이에요.
"""

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from tortoise import Tortoise

from app.core import config
from app.core.config import Env
from app.core.db.databases import TORTOISE_ORM
from app.models.children import Child
from app.models.guardians import Guardian
from app.models.medications import DosageForm, Medication, Route
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType

DEMO_CHILD: dict[str, Any] = {
    "name": "예시아이",
    "birth_date": date(2023, 4, 2),
    "weight_kg": Decimal("16.90"),
    "allergies": "계란",
    "notes": "시드 스크립트로 만든 예시 자녀",
}

DEMO_PRESCRIPTION: dict[str, Any] = {
    "source_type": SourceType.PRESCRIPTION,
    "status": PrescriptionStatus.OCR_DONE,
    "prescription_date": date(2026, 11, 12),
    "hospital_name": "해솔소아청소년과의원",
    "diagnosis_extracted": "J00,J209",
}

# OCR이 읽은 값 = ocr_value_snapshot. 확정할 때 이 값과 다르면 is_user_edited=True가 된다.
DEMO_MEDICATIONS: list[dict[str, Any]] = [
    {
        "name": "세파클러건조시럽(내복)/60(1)mL/병",
        "dose_per_time": 4.2,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "1일 3회 식후 30분",
        "route": "ORAL",
        "dosage_form": "DRY_SYRUP",
        "confidence": 0.93,
    },
    {
        "name": "뮤코펙트시럽(암브록솔염산염)",
        "dose_per_time": 3.0,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "1일 3회 식후 30분",
        "route": "ORAL",
        "dosage_form": "SYRUP",
        "confidence": 0.95,
    },
    {
        "name": "비오플250산",
        "dose_per_time": 0.5,
        "unit": "포",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "1일 3회 식후 30분",
        "route": "ORAL",
        "dosage_form": "POWDER",
        "confidence": 0.9,
    },
    {
        "name": "세토펜현탁액(아세트아미노펜)",
        "dose_per_time": 5.0,
        "unit": "mL",
        "daily_count": None,
        "total_days": 3,
        "as_needed": True,
        "max_daily_count": None,  # OCR이 못 읽음 → 보호자가 확정 화면에서 채워야 함
        "usage": "열날 때 4시간 이상 간격",
        "route": "ORAL",
        "dosage_form": "SYRUP",
        "confidence": 0.72,
    },
]


async def create_demo_prescription(guardian: Guardian) -> Prescription:
    """보호자의 예시 아이 밑에 OCR_DONE 처방 1건과 약 4개를 만든다. 테스트에서도 이 함수를 쓴다."""
    child = await Child.filter(guardian_id=guardian.id, name=DEMO_CHILD["name"]).first()
    if child is None:
        child = await Child.create(guardian_id=guardian.id, consent_agreed_at=datetime.now(UTC), **DEMO_CHILD)
    p = await Prescription.create(child_id=child.id, **DEMO_PRESCRIPTION)
    for m in DEMO_MEDICATIONS:
        values = {k: v for k, v in m.items() if k != "confidence"}
        await Medication.create(
            prescription_id=p.id,
            confidence=Decimal(str(m["confidence"])),
            ocr_value_snapshot=values,
            is_user_edited=False,
            **{
                **values,
                "dose_per_time": Decimal(str(values["dose_per_time"])),
                "route": Route(values["route"]),
                "dosage_form": DosageForm(values["dosage_form"]),
            },
        )
    return p


def confirm_body_example(meds: list[Medication]) -> dict[str, Any]:
    """확정 API에 넣을 예시 본문: OCR 값 그대로 + 진단명 입력 + 해열제 하루 최대 횟수만 채움."""
    items = []
    for m in meds:
        items.append(
            {
                "medication_id": m.id,
                "name": m.name,
                "dose_per_time": float(m.dose_per_time) if m.dose_per_time is not None else None,
                "unit": m.unit,
                "daily_count": m.daily_count,
                "total_days": m.total_days,
                "as_needed": m.as_needed,
                "max_daily_count": 4 if m.as_needed else None,
                "usage": m.usage,
                "route": m.route.value if m.route else None,
                "dosage_form": m.dosage_form.value if m.dosage_form else None,
            }
        )
    return {
        "prescription_date": "2026-11-12",
        "hospital_name": "해솔소아청소년과의원",
        "diagnosis_user_input": "감기, 급성 기관지염",
        "symptom_notes": "기침이 심하고 밤에 열이 나요",
        "medications": items,
    }


async def seed(email: str) -> None:
    if config.ENV == Env.PROD:
        raise SystemExit("ENV=prod 에서는 예시 처방을 만들지 않아요.")
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        guardian = await Guardian.get_or_none(email=email.lower())
        if guardian is None:
            raise SystemExit(f"{email} 계정이 없어요. 먼저 /api/v1/auth/signup 으로 가입해 주세요.")
        p = await create_demo_prescription(guardian)
        meds = await Medication.filter(prescription_id=p.id).order_by("id")
        print(f"\n만들었어요: prescription_id = {p.id} (상태 {p.status}, 약 {len(meds)}개)\n")
        print(f"1) PUT  /api/v1/prescriptions/{p.id}/confirm  ← 아래 JSON을 Request body에 붙여 넣기")
        print(json.dumps(confirm_body_example(meds), ensure_ascii=False, indent=2))
        print(f"\n2) POST /api/v1/prescriptions/{p.id}/guide   (본문 없음, 약 20초)")
        print(f"3) GET  /api/v1/prescriptions/{p.id}/guide")
    finally:
        await Tortoise.close_connections()


def main() -> None:
    parser = argparse.ArgumentParser(description="개발 DB에 예시 처방(OCR_DONE)을 넣어요.")
    parser.add_argument("--email", required=True, help="처방을 붙일 내 계정 이메일")
    asyncio.run(seed(parser.parse_args().email))


if __name__ == "__main__":
    main()
