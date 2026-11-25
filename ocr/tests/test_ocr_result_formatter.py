import pytest

from ocr.ocr_result_formatter import (
    display_drug_name,
    format_bag_guide_medication,
    format_prescription_medication,
    infer_dosage_form,
    infer_prescription_unit,
    infer_route,
    normalize_unit,
)


@pytest.mark.parametrize(
    ("name", "hints", "dosage_form", "route"),
    [
        ("세파클러건조시럽(내복)/60(1)mL/병", (), "DRY_SYRUP", "ORAL"),
        ("클래리시드건조사립125mg/5mL/50(1)mL/병", (), "DRY_SYRUP", "ORAL"),  # OCR 오타 '사립'
        ("세토펜현탁액(아세트아미노펜)/100(1)mL/병", (), "SYRUP", "ORAL"),
        ("비오플250산(사카로마이세스보울라디)/1포", (), "POWDER", "ORAL"),
        ("옴니세프세립", (), "POWDER", "ORAL"),
        ("레보세티리진정5mg", (), "TABLET", "ORAL"),
        ("타미플루캡슐30mg", (), "CAPSULE", "ORAL"),
        ("후시딘연고", (), "OINTMENT", "EXTERNAL"),
        ("로코이드크림0.1%", (), "CREAM", "EXTERNAL"),
        ("크라비트점안액0.5%", (), "EYE_DROP", "EXTERNAL"),
        ("써스펜좌약125mg", (), "SUPPOSITORY", "EXTERNAL"),
        ("벤토린에보할러", (), "ETC", "EXTERNAL"),
        ("타리비드이용액0.3%", (), "ETC", "EXTERNAL"),
        # 성상에 '현탁액'이 있어도 뿌리는 약은 먹는 시럽으로 보면 안 된다.
        ("나조넥스나잘스프레이", ("비강용 스테로이드", "흰색 비강 분무 현탁액"), "ETC", "EXTERNAL"),
        ("모르는약", (), None, None),
    ],
)
def test_infer_dosage_form_and_route(name, hints, dosage_form, route):
    assert infer_dosage_form(name, *hints) == dosage_form
    assert infer_route(dosage_form, name, *hints) == route


@pytest.mark.parametrize(
    ("name", "unit"),
    [
        ("세파클러건조시럽(내복)/60(1)mL/병", "mL"),
        ("비오플250산(사카로마이세스보울라디)/1포", "포"),
        ("부루펜정200밀리그램(이부프로펜)/1정", "정"),
        ("써스펜좌약125mg(아세트아미노펜)/1개", "개"),
        ("풀미코트레스플0.5mg/2mL(부데소니드)/1관", None),  # 마지막 단위 '관'은 허용 목록에 없다
        ("크라비트점안액0.5%(러보플록사신)/5mL/병", "방울"),
        ("타리비드이용액0.3%(오플록사신)/5mL/병", "방울"),
    ],
)
def test_infer_prescription_unit_uses_last_package_unit(name, unit):
    assert infer_prescription_unit(name, infer_dosage_form(name)) == unit


@pytest.mark.parametrize(("raw", "unit"), [("ml", "mL"), ("cc", "mL"), ("포", "포"), ("분무", None), (None, None)])
def test_normalize_unit_keeps_only_allowed_units(raw, unit):
    assert normalize_unit(raw) == unit


def test_as_needed_prescription_drug_has_no_daily_count_but_max_daily_count():
    drug = {"코드": "652600871", "명칭": "세토펜현탁액/100(1)mL/병", "1회투약량": 5, "1일투여횟수": 4,
            "총투약일수": 3, "용법": "필요시 1일 최대 4회", "신뢰도": 0.9}  # fmt: skip

    medication = format_prescription_medication(drug)

    assert medication["as_needed"] is True
    assert medication["daily_count"] is None
    assert medication["max_daily_count"] == 4
    assert medication["dose_per_time"] == 5.0
    assert medication["confidence"] == 0.9


def test_usage_arrow_is_removed():
    drug = {"코드": "643901230", "명칭": "세파클러건조시럽(내복)/60(1)mL/병", "1회투약량": 4.2,
            "1일투여횟수": 3, "총투약일수": 5, "용법": "->식후 30분"}  # fmt: skip

    assert format_prescription_medication(drug)["usage"] == "식후 30분"


def test_bag_taking_time_applies_only_to_oral_regular_drugs():
    oral = {"명칭": "부루펜시럽", "분류": "해열진통제", "1회용량": 5, "단위": "mL", "1일횟수": 3, "일수": 3}
    ointment = {"명칭": "후시딘연고", "분류": "외용 항생제", "1회용량": "적당량", "1일횟수": 2, "일수": 7}

    assert format_bag_guide_medication(oral, "식후 30분")["usage"] == "식후 30분"
    external = format_bag_guide_medication(ointment, "식후 30분")
    assert external["usage"] == "적당량"
    assert external["dose_per_time"] is None
    assert external["route"] == "EXTERNAL"


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("맥시부펜시럽(덱시부프로펜)/100(1)mL/병", "맥시부펜시럽"),
        ("돔페리돈현탁액1mg/mL/100(1)mL/병", "돔페리돈현탁액1mg"),
        ("세파클러건조시럽 (내복)", "세파클러건조시럽"),
        ("오논드라이시럽（프란루카스트수화물）", "오논드라이시럽"),  # 전각 괄호
        ("옴니세프세립", "옴니세프세립"),
        ("(급여)타이레놀", "(급여)타이레놀"),  # 앞에 남는 글자가 없으면 원래 이름
    ],
)
def test_display_drug_name_keeps_text_before_parenthesis_or_slash(raw, shown):
    assert display_drug_name(raw) == shown


def test_name_is_shortened_but_unit_still_comes_from_package_notation():
    med = format_prescription_medication({"명칭": "맥시부펜시럽(덱시부프로펜)/100(1)mL/병", "1회투약량": 4})
    assert med["name"] == "맥시부펜시럽"
    assert med["unit"] == "mL"
    assert med["dosage_form"] == "SYRUP"
