from enum import StrEnum

from tortoise import fields, models


class SourceType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    PILL_BAG = "PILL_BAG"


class PrescriptionStatus(StrEnum):
    UPLOADED = "UPLOADED"
    OCR_DONE = "OCR_DONE"
    CONFIRMED = "CONFIRMED"
    GUIDE_DONE = "GUIDE_DONE"
    FAILED = "FAILED"


class Prescription(models.Model):
    """처방전 (ERD v1.1 2.3 PRESCRIPTION).

    마이그레이션에서 직접 추가하는 것 (Tortoise가 표현하지 못함):
    - CHECK chk_prescription_source_type, chk_prescription_status, chk_prescription_diagnosis
    - INDEX idx_prescription_child_created (child_id, created_at DESC)
    """

    id = fields.BigIntField(primary_key=True, source_field="prescription_id")
    child: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Child",
        related_name="prescriptions",
        on_delete=fields.CASCADE,
        source_field="child_id",
    )
    source_type = fields.CharEnumField(SourceType, max_length=20)
    status = fields.CharEnumField(PrescriptionStatus, max_length=20)
    prescription_date = fields.DateField(null=True, description="처방전 교부일. 약봉투는 항상 NULL")
    hospital_name = fields.CharField(max_length=100, null=True)
    diagnosis_extracted = fields.CharField(
        max_length=50, null=True, description="OCR 질병분류기호 쉼표 연결 (참고용). 약봉투는 항상 NULL"
    )
    diagnosis_user_input = fields.CharField(
        max_length=200, null=True, description="보호자 입력 병명. CONFIRMED/GUIDE_DONE 시 필수·비공백"
    )
    symptom_notes = fields.TextField(null=True)
    image_storage_key = fields.CharField(max_length=512, null=True, description="S3 키. 가이드 생성 후 NULL")
    raw_text_masked = fields.TextField(null=True, description="마스킹된 OCR 원문. API 응답·로그 노출 금지")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "prescription"
        table_description = "처방전"
