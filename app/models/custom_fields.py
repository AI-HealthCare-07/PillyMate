from tortoise import fields


class TinyIntField(fields.SmallIntField):
    """MySQL TINYINT (-128 ~ 127). Tortoise에 기본 제공되지 않아 직접 정의한다."""

    SQL_TYPE = "TINYINT"

    @property
    def constraints(self) -> dict:
        return {"ge": -128, "le": 127}
