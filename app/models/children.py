from tortoise import fields, models


class Child(models.Model):
    """자녀 (ERD v1.1 2.2 CHILD).

    DB CHECK: chk_child_weight_kg (0.5 ~ 150.0) — 마이그레이션에서 추가.
    """

    id = fields.BigIntField(primary_key=True, source_field="child_id")
    guardian: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Guardian",
        related_name="children",
        on_delete=fields.CASCADE,
        source_field="guardian_id",
    )
    name = fields.CharField(max_length=50)
    birth_date = fields.DateField(description="만 18세 미만만 허용 (서버 검증)")
    weight_kg = fields.DecimalField(max_digits=5, decimal_places=2, null=True, description="0.5 ~ 150.0")
    allergies = fields.TextField(null=True)
    notes = fields.TextField(null=True)
    consent_agreed_at = fields.DatetimeField(description="보호자 동의 3항목 완료 시각")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "child"
        table_description = "자녀"
