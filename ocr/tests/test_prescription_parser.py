import math

import pytest

from ocr import prescription_parser
from ocr.tests.fake_clova_fields import fake_prescription_fields, rotate_fields


@pytest.mark.parametrize("angle_degrees", [0, 3, -3])
def test_reads_every_prescription_item_even_when_photo_is_tilted(angle_degrees):
    fields = rotate_fields(fake_prescription_fields(), math.radians(angle_degrees))

    result = prescription_parser.parse(fields)

    assert result["보험종류"] == "건강보험"
    assert result["요양기관기호"] == "31283746"
    assert result["교부일"] == "2026-11-12"
    assert result["교부번호"] == "00231"
    assert result["환자"] == {"성명": "김하윤", "주민등록번호": "230512-4083217"}
    assert result["의료기관"]["명칭"] == "해솔소아청소년과의원"
    assert result["의료기관"]["전화번호"] == "031-764-2210"
    assert result["질병분류기호"] == ["J00", "J209"]
    assert result["처방의료인"] == {"성명": "박정민", "면허종별": "의사", "면허번호": "84213"}
    assert result["사용기간_일"] == 3


def test_reads_drug_table_columns_by_position():
    drugs = prescription_parser.parse(fake_prescription_fields())["처방의약품"]

    assert [(d["코드"], d["1회투약량"], d["1일투여횟수"], d["총투약일수"]) for d in drugs] == [
        ("643901230", 4.2, 3, 5),
        ("652600871", 5, 4, 3),
    ]
    assert drugs[0]["명칭"] == "세파클러건조시럽(내복)/60(1)mL/병"
    assert drugs[0]["용법"] == "->식후 30분"
    assert drugs[0]["신뢰도"] == 0.95


def test_empty_fields_give_none():
    assert prescription_parser.parse([]) is None


@pytest.mark.parametrize(
    ("ocr_text", "expected"),
    [("s800", "S800"), ("J2O9", "J209"), ("J0", None), ("800", None)],
)
def test_normalize_disease_code_fixes_common_ocr_mistakes(ocr_text, expected):
    assert prescription_parser.normalize_disease_code(ocr_text) == expected
