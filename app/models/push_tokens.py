from tortoise import fields, models


class PushToken(models.Model):
    """웹 푸시 구독 (ERD v1.1 2.6 PUSH_TOKEN, VAPID 방식).

    브라우저 PushSubscription 값을 저장한다. token = endpoint 주소.
    token 컬럼은 마이그레이션에서 COLLATE utf8mb4_bin(대소문자 구분)으로 바꾼다.
    """

    id = fields.BigIntField(primary_key=True, source_field="push_token_id")
    guardian: fields.ForeignKeyRelation = fields.ForeignKeyField(
        "models.Guardian",
        related_name="push_tokens",
        on_delete=fields.CASCADE,
        source_field="guardian_id",
    )
    token = fields.CharField(max_length=512, unique=True)  # 구독 endpoint
    p256dh = fields.CharField(max_length=255)  # 브라우저 공개 키 (메시지 암호화용)
    auth = fields.CharField(max_length=255)  # 브라우저 인증 비밀값
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "push_token"
        table_description = "웹 푸시 구독"
