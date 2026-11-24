from typing import Any

from tortoise import fields, models


class Guide(models.Model):
    """맞춤형 복약 가이드 (ERD v1.1 2.5 GUIDE). 처방전과 1:0..1."""

    id = fields.BigIntField(primary_key=True, source_field="guide_id")
    prescription: fields.OneToOneRelation = fields.OneToOneField(
        "models.Prescription",
        related_name="guide",
        on_delete=fields.CASCADE,
        source_field="prescription_id",
    )
    guide_content: dict[str, Any] = fields.JSONField(
        description="summary, medications, warning_signs, care_tips, disclaimer 5개 고정 키"
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide"
        table_description = "맞춤형 복약 가이드"
