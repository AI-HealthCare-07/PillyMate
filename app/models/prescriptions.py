"""처방·약·가이드 테이블 (ERD v1.0, 2026-11-24).

- 자녀(Child)는 app/models/children.py에 있다. (BE-1의 로그인 응답 child_count가 그 경로를 읽는다)
- 코드값은 MySQL ENUM 대신 글자 칸(VARCHAR)에 넣는다 (ERD 4-3: aerich 마이그레이션 충돌 방지).
- 필요시 약 규칙(as_needed면 daily_count 없음, max_daily_count 있음)은 서비스에서 검사한다.

ERD대로 만든 DB 테이블 4개: child, prescription, medication, guide
"""

from enum import StrEnum

from tortoise import fields, models

from app.models.children import Child


class SourceType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    PILL_BAG = "PILL_BAG"


class PrescriptionStatus(StrEnum):
    UPLOADED = "UPLOADED"
    OCR_DONE = "OCR_DONE"
    CONFIRMED = "CONFIRMED"
    GUIDE_DONE = "GUIDE_DONE"
    FAILED = "FAILED"


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


class Prescription(models.Model):
    id = fields.BigIntField(primary_key=True, source_field="prescription_id")
    child: fields.ForeignKeyRelation[Child] = fields.ForeignKeyField(
        "models.Child", related_name="prescriptions", on_delete=fields.CASCADE
    )
    source_type = fields.CharEnumField(enum_type=SourceType, max_length=20)
    status = fields.CharEnumField(enum_type=PrescriptionStatus, max_length=20, default=PrescriptionStatus.UPLOADED)
    prescription_date = fields.DateField(null=True)
    hospital_name = fields.CharField(max_length=100, null=True)
    diagnosis_extracted = fields.CharField(max_length=20, null=True)
    diagnosis_user_input = fields.CharField(max_length=200, null=True)
    symptom_notes = fields.TextField(null=True)
    image_storage_key = fields.CharField(max_length=512, null=True)
    raw_text_masked = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    medications: fields.ReverseRelation["Medication"]
    guide: fields.BackwardOneToOneRelation["Guide"]

    class Meta:
        table = "prescription"


class Medication(models.Model):
    id = fields.BigIntField(primary_key=True, source_field="medication_id")
    prescription: fields.ForeignKeyRelation[Prescription] = fields.ForeignKeyField(
        "models.Prescription", related_name="medications", on_delete=fields.CASCADE, db_index=True
    )
    name = fields.CharField(max_length=100)
    insurance_code = fields.CharField(max_length=20, null=True)
    dose_per_time = fields.DecimalField(max_digits=7, decimal_places=2, null=True)
    unit = fields.CharField(max_length=10, null=True)
    daily_count = fields.SmallIntField(null=True)
    total_days = fields.SmallIntField(null=True)
    as_needed = fields.BooleanField(default=False)
    max_daily_count = fields.SmallIntField(null=True)
    usage = fields.CharField(max_length=100, null=True)
    route = fields.CharEnumField(enum_type=Route, max_length=10, null=True)
    dosage_form = fields.CharEnumField(enum_type=DosageForm, max_length=20, null=True)
    confidence = fields.DecimalField(max_digits=3, decimal_places=2, null=True)
    ocr_value_snapshot = fields.JSONField(null=True)
    is_user_edited = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication"


class Guide(models.Model):
    id = fields.BigIntField(primary_key=True, source_field="guide_id")
    prescription: fields.OneToOneRelation[Prescription] = fields.OneToOneField(
        "models.Prescription", related_name="guide", on_delete=fields.CASCADE
    )
    guide_content = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide"
