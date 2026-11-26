from tortoise import fields, models


class Guardian(models.Model):
    """보호자 (ERD v1.0 2.1 GUARDIAN).

    코드에서는 `guardian.id`로 쓰고, DB 컬럼 이름은 ERD대로 `guardian_id`다.
    """

    id = fields.BigIntField(primary_key=True, source_field="guardian_id")
    email = fields.CharField(max_length=255, unique=True, description="소문자 정규화 저장")
    password_hash = fields.CharField(max_length=255, description="bcrypt 해시")
    name = fields.CharField(max_length=50)
    birth_date = fields.DateField(description="가입 시 만 19세 이상 서버 검증")
    gender = fields.CharField(max_length=10, null=True, description="MALE | FEMALE (이전 가입자는 NULL)")
    phone_number = fields.CharField(max_length=20, null=True, description="숫자만 저장 (예: 01012345678)")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "guardian"
        table_description = "보호자"
