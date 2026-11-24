"""자녀 테이블 (ERD v1.0 2.2 CHILD). 보호자(guardian) 1명이 자녀 여러 명을 둔다.

자녀 등록·수정 API는 BE-2 담당. 처방 확정·가이드 API가 먼저 쓰려고 ERD대로 모델만 만들어 두었다.
"""

from tortoise import fields, models

from app.models.guardians import Guardian


class Child(models.Model):
    id = fields.BigIntField(primary_key=True, source_field="child_id")
    guardian: fields.ForeignKeyRelation[Guardian] = fields.ForeignKeyField(
        "models.Guardian", related_name="children", on_delete=fields.CASCADE, db_index=True
    )
    name = fields.CharField(max_length=50)
    birth_date = fields.DateField()
    weight_kg = fields.DecimalField(max_digits=5, decimal_places=2, null=True)
    allergies = fields.TextField(null=True)
    notes = fields.TextField(null=True)
    consent_agreed_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "child"
