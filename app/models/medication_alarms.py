from tortoise import fields, models


class MedicationAlarm(models.Model):
    """복약 알림 스케줄 (ERD v1.1 2.7 MEDICATION_ALARM, P1~P6 초안)."""

    id = fields.BigIntField(primary_key=True, source_field="alarm_id")
    medication: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Medication",
        related_name="alarms",
        on_delete=fields.CASCADE,
        source_field="medication_id",
    )
    notify_time = fields.TimeField()
    start_date = fields.DateField()
    end_date = fields.DateField(description="start_date + total_days - 1 (종료일 포함)")
    is_enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "medication_alarm"
        table_description = "복약 알림 스케줄"
        unique_together = (("medication", "notify_time", "start_date"),)
