from enum import StrEnum
from typing import Any

from tortoise import fields, models

from app.models.custom_fields import TinyIntField


class MedicationUnit(StrEnum):
    ML = "mL"
    PACKET = "포"
    TABLET = "정"
    CAPSULE = "캡슐"
    GRAM = "g"
    DROP = "방울"
    PIECE = "개"


class Route(StrEnum):
    ORAL = "ORAL"
    EXTERNAL = "EXTERNAL"


class DosageForm(StrEnum):
    SYRUP = "SYRUP"
    DRY_SYRUP = "DRY_SYRUP"
    POWDER = "POWDER"
    TABLET = "TABLET"
    CAPSULE = "CAPSULE"
    OINTMENT = "OINTMENT"
    CREAM = "CREAM"
    EYE_DROP = "EYE_DROP"
    SUPPOSITORY = "SUPPOSITORY"
    ETC = "ETC"


class Medication(models.Model):
    """처방 약품 (ERD v1.1 2.4 MEDICATION).

    마이그레이션에서 직접 추가하는 CHECK: chk_medication_unit, chk_medication_route,
    chk_medication_dosage_form, chk_medication_as_needed, chk_medication_confidence.
    route·dosage_form·max_daily_count(필요시 약)의 "확정 시 필수"는 확정 API에서 검증한다 (ERD 4절).
    """

    id = fields.BigIntField(primary_key=True, source_field="medication_id")
    prescription: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Prescription",
        related_name="medications",
        on_delete=fields.CASCADE,
        source_field="prescription_id",
    )
    name = fields.CharField(max_length=100)
    insurance_code = fields.CharField(max_length=20, null=True, description="처방전 9자리. 약봉투는 항상 NULL")
    dose_per_time = fields.DecimalField(max_digits=8, decimal_places=4, null=True)
    unit = fields.CharEnumField(MedicationUnit, max_length=10, null=True)
    daily_count = TinyIntField(null=True, description="as_needed=1이면 NULL")
    total_days = fields.SmallIntField(null=True)
    as_needed = fields.BooleanField(default=False)
    max_daily_count = TinyIntField(null=True, description="필요시 약 확정 시 필수 (앱 검증)")
    usage = fields.CharField(max_length=100, null=True)
    route = fields.CharEnumField(Route, max_length=10, null=True)
    dosage_form = fields.CharEnumField(DosageForm, max_length=20, null=True)
    confidence = fields.DecimalField(max_digits=3, decimal_places=2, null=True, description="0.00 ~ 1.00")
    ocr_value_snapshot: dict[str, Any] | None = fields.JSONField(
        null=True, description="최초 OCR 불변 스냅샷 (run_ocr 약품 dict)"
    )
    is_user_edited = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication"
        table_description = "처방 약품"
