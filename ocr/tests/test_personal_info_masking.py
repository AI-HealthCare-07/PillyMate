import pytest

from ocr.personal_info_masking import mask_personal_info, mask_personal_info_in_fields
from ocr.tests.fake_clova_fields import fake_field


def test_saved_fields_get_dummy_values_that_keep_the_same_shape():
    fields = [fake_field("김하윤(만", 10, 10), fake_field("230512-4083217", 10, 40), fake_field("[항생제]", 10, 70)]

    masked = mask_personal_info_in_fields(fields, ["김하윤"])

    assert [f["inferText"] for f in masked] == ["홍길동(만", "000000-0000000", "[항생제]"]
    assert [f["boundingPoly"] for f in masked] == [f["boundingPoly"] for f in fields]
    assert fields[0]["inferText"] == "김하윤(만"  # 원본은 바꾸지 않는다


def test_masks_resident_number_including_partly_hidden_form():
    text = "주민등록번호 230512-4083217 / 보호자 230512-4******"

    assert mask_personal_info(text) == "주민등록번호 [주민번호] / 보호자 [주민번호]"


def test_masks_patient_name_found_by_parser_everywhere():
    text = "환자 김하윤 님 ... 김하윤 어린이 복약안내"

    assert mask_personal_info(text, ["김하윤"]) == "환자 [이름] 님 ... [이름] 어린이 복약안내"


def test_masks_name_right_after_name_label_even_if_parser_missed_it():
    text = "성 명\n김하운\n환자정보 : 이서준(만 5세)"

    assert mask_personal_info(text) == "성 명\n[이름]\n환자정보 : [이름]([나이])"


def test_does_not_mask_next_label_when_name_cell_is_empty():
    assert mask_personal_info("성 명 주민등록번호") == "성 명 주민등록번호"


def test_ignores_empty_and_one_letter_names():
    assert mask_personal_info("가나다", [None, "", "가"]) == "가나다"


@pytest.mark.parametrize(
    "phone",
    ["031-764-2210", "02-123-4567", "010-1234-5678", "(02)123-4567", "(031) 764-2210", "031 - 764 - 2210", "1588-1234"],
)
def test_masks_phone_and_fax_numbers(phone):
    assert mask_personal_info(f"전화번호 {phone} 끝") == "전화번호 [전화번호] 끝"


@pytest.mark.parametrize(
    "not_phone",
    [
        "영수증번호 2026-1112-0042",  # 0이나 15~19로 시작하지 않는 4-4-4 숫자
        "사업자등록번호 123-45-67890",
        "조제일자 2026-11-12",
        "643901230 세파클러건조시럽",  # 보험코드
        "요양기관기호 31283746",
    ],
)
def test_does_not_mask_numbers_that_are_not_phone_numbers(not_phone):
    assert mask_personal_info(not_phone) == not_phone


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("환자정보 : 김하윤(만 3세)", "환자정보 : [이름]([나이])"),
        ("만3세 2개월", "[나이]"),
        ("생후 8개월 영아", "[나이] 영아"),
        ("환자정보: 이서준 (6개월)", "환자정보: [이름] ([나이])"),
        ("[이름] (만 1세(18개월))", "[이름] ([나이]([나이]))"),
        ("3일분 복용", "3일분 복용"),  # 복용 일수는 나이가 아니다
        ("실온보관, 개봉 후 1개월", "실온보관, 개봉 후 1개월"),  # 보관 기간은 나이가 아니다
    ],
)
def test_masks_age(text, masked):
    assert mask_personal_info(text, ["김하윤"]) == masked
