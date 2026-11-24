import math

import pytest

from ocr import medicine_bag_parser
from ocr.tests.fake_clova_fields import fake_medicine_bag_fields, rotate_fields


@pytest.mark.parametrize("angle_degrees", [0, 2, -2])
def test_reads_guide_panel_drug_cards(angle_degrees):
    fields = rotate_fields(fake_medicine_bag_fields(), math.radians(angle_degrees))

    drugs = medicine_bag_parser.parse(fields)["약품"]

    assert [d["명칭"] for d in drugs] == ["세파클러건조시럽", "세토펜현탁액", "후시딘연고"]
    assert [d["분류"] for d in drugs] == ["항생제", "해열진통제", "외용 항생제"]
    assert (drugs[0]["1회용량"], drugs[0]["단위"], drugs[0]["1일횟수"], drugs[0]["일수"]) == (4.2, "mL", 3, 5)
    assert drugs[0]["성상"] == "분홍색 현탁액"
    assert drugs[0]["보관"] == "냉장 보관"
    assert drugs[1]["필요시"] is True
    assert drugs[1]["주의사항"] == "1일 최대 4회"
    assert drugs[2]["1회용량"] == "적당량"


def test_reads_patient_hospital_and_taking_time():
    result = medicine_bag_parser.parse(fake_medicine_bag_fields())

    assert result["복약안내"]["환자"] == {"성명": "김하윤", "나이": 3}
    assert result["복약안내"]["병원"] == "해솔소아청소년과의원"
    assert result["복약안내"]["다음내방일"] == "2026-11-19"
    assert result["복용표시"] == {"1일횟수": 3, "일분": 5, "복용시점": "식후 30분"}


def test_reads_receipt_panel_separately_from_guide_panel():
    receipt = medicine_bag_parser.parse(fake_medicine_bag_fields())["영수증"]

    assert receipt["환자성명"] == "김하윤"
    assert receipt["약제비총액"] == 15300
    assert receipt["본인부담금"] == 4600
    assert [(d["명칭"], d["투약량"], d["횟수"], d["일수"]) for d in receipt["약품내역"]] == [
        ("세파클러건조시럽", 4.2, 3, 5),
        ("비오플250산", 1, 2, 5),
    ]


def test_bag_without_category_labels_has_no_guide_drugs():
    fields = [f for f in fake_medicine_bag_fields() if not f["inferText"].startswith("[")]

    assert medicine_bag_parser.parse(fields)["약품"] == []


@pytest.mark.parametrize(
    ("dose_text", "expected"),
    [
        ("1정씩 3회 14일분", {"1회용량": 1, "단위": "정", "1일횟수": 3, "일수": 14, "필요시": False}),
        ("5mL씩 필요시", {"1회용량": 5, "단위": "mL", "1일횟수": None, "일수": None, "필요시": True}),
        ("적당량 2회 7일분", {"1회용량": "적당량", "단위": None, "1일횟수": 2, "일수": 7, "필요시": False}),
    ],
)
def test_parse_dose_text(dose_text, expected):
    assert medicine_bag_parser.parse_dose(dose_text) == expected
