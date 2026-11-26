from tortoise import fields, models


class MedicationDoseLog(models.Model):
    """복약 체크 기록 — 그날 그 먹는 때에 약을 먹였는지 (11/26 추가, ERD 반영 예정).

    행이 없으면 '기록 없음', is_taken=false면 '안 먹임(미복용)', true면 '먹임'.
    slot은 화면의 먹는 때(아침·점심·저녁·자기 전)이고, 약의 하루 횟수·용법으로 정해진 때만 저장한다.
    """

    id = fields.BigIntField(primary_key=True, source_field="dose_log_id")
    medication: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Medication",
        related_name="dose_logs",
        on_delete=fields.CASCADE,
        source_field="medication_id",
    )
    dose_date = fields.DateField(description="먹인 날 (KST)")
    slot = fields.CharField(max_length=10, description="먹는 때: 아침·점심·저녁·자기 전")
    is_taken = fields.BooleanField(description="true 먹임 / false 안 먹임")
    checked_at = fields.DatetimeField(auto_now=True, description="마지막으로 체크하거나 취소한 시각")

    class Meta:
        table = "medication_dose_log"
        table_description = "복약 체크 기록"
        unique_together = (("medication", "dose_date", "slot"),)
