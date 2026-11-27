"""약효 분류 조회(drug_lookup) 테스트. DB 없이 돈다.

아래 품목 데이터는 테스트용으로 만든 것이다. 분류번호·보험코드·성상은 실제 허가정보와 다를 수 있다.
"""

import pytest

from app.services import drug_lookup
from app.services.drug_lookup import (
    DrugIndex,
    DrugRecord,
    Efficacy,
    atc_label,
    class_label,
    clean_printed_class,
    efficacy_for,
    find_by_insurance_code,
    find_by_name,
    load_records,
    parse_name,
)

RECORDS = [
    DrugRecord(
        "지스로맥스정250밀리그램(아지트로마이신수화물)",
        "614",
        None,
        "아지트로마이신",
        "600000001",
        "분홍색 장방형 필름코팅정",
    ),
    DrugRecord("지스로맥스건조시럽(아지트로마이신수화물)", "614", None, "아지트로마이신", "600000002", "흰색 가루"),
    DrugRecord("타이레놀정500밀리그람(아세트아미노펜)", "114", None, "아세트아미노펜", "600000003", "흰색 장방형 정제"),
    DrugRecord("타이레놀정160밀리그램(아세트아미노펜)", "114", None, "아세트아미노펜", "600000004", "흰색 원형 정제"),
    DrugRecord("시네츄라시럽", "222", None, None, "600000005", "갈색 시럽"),
    DrugRecord("뮤코솔시럽(암브록솔염산염)", "222", None, "암브록솔염산염", "600000006", "무색 시럽"),
    # 상표는 같은데 분류가 다른 경우 (애매함 시험용)
    DrugRecord("헷갈림정10밀리그램", "114", None, None, "600000007", None),
    DrugRecord("헷갈림정20밀리그램", "141", None, None, "600000008", None),
    # 분류번호 표에 없는 분류 → 데이터의 분류명을 그대로 쓴다
    DrugRecord(
        "엘도스캡슐300밀리그램(에르도스테인)",
        "999",
        "[999]테스트분류",
        "에르도스테인",
        "600000009",
        "녹색 흰색 경질캡슐",
    ),
]


@pytest.fixture(scope="module")
def index() -> DrugIndex:
    return DrugIndex(RECORDS)


# ------------------------------------------------------------------ 이름 쪼개기


@pytest.mark.parametrize(
    ("name", "stem", "form", "strength", "ingredient"),
    [
        ("지스로맥스정250mg", "지스로맥스", "정", "250mg", None),
        ("지스로맥스정250밀리그램(아지트로마이신수화물)", "지스로맥스", "정", "250mg", "아지트로마이신"),
        ("세파클러건조시럽(내복)/60(1)mL/병", "세파클러", "건조시럽", None, None),
        ("엘도스캡슐300mg", "엘도스", "캡슐", "300mg", None),
        ("시네츄라시럽", "시네츄라", "시럽", None, None),
        ("헥사메딘액0.12%", "헥사메딘", "액", "0.12%", None),
        ("타이레놀정 500 mg", "타이레놀", "정", "500mg", None),
        ("뮤코펙트시럽(암브록솔염산염)", "뮤코펙트", "시럽", None, "암브록솔"),
    ],
)
def test_parse_name(name, stem, form, strength, ingredient):
    p = parse_name(name)
    assert (p.stem, p.form, p.strength, p.ingredient) == (stem, form, strength, ingredient)


def test_clean_printed_class():
    assert clean_printed_class("[항생제]") == "항생제"
    assert clean_printed_class("  ") is None
    assert clean_printed_class(None) is None


# ------------------------------------------------------------------ 이름으로 찾기


def test_exact_match(index):
    r = find_by_name(index, "타이레놀정500mg", unit="정", chart="흰색 장방형 정제")
    assert r.efficacy == Efficacy("해열진통제", "name_lookup", "exact")


def test_several_products_same_class_is_ok(index):
    # 함량이 없으면 타이레놀정 500·160 둘 다 남지만 분류가 같으니 쓴다
    r = find_by_name(index, "타이레놀정")
    assert r.efficacy == Efficacy("해열진통제", "name_lookup", "class_agree")
    assert len(r.candidates) == 2


def test_form_narrows_candidates(index):
    r = find_by_name(index, "지스로맥스정250mg", unit="정")
    assert r.efficacy is not None and r.efficacy.label == "항생제"
    assert [c.item_name for c in r.candidates] == ["지스로맥스정250밀리그램(아지트로마이신수화물)"]


def test_different_classes_is_ambiguous(index):
    r = find_by_name(index, "헷갈림정")
    assert r.efficacy is None
    assert "분류가 서로 달라요" in r.reason


def test_strength_resolves_ambiguity(index):
    r = find_by_name(index, "헷갈림정20mg")
    assert r.efficacy == Efficacy("항히스타민제", "name_lookup", "exact")


def test_unit_mismatch_drops_candidate(index):
    # 이름은 정제인데 약봉투 단위가 mL → 맞는 품목이 없다
    r = find_by_name(index, "타이레놀정500mg", unit="mL")
    assert r.efficacy is None


def test_color_mismatch_drops_candidate(index):
    r = find_by_name(index, "타이레놀정500mg", chart="빨간색 원형 정제")
    assert r.efficacy is None


def test_efficacy_text_mismatch_is_rejected(index):
    r = find_by_name(index, "타이레놀정500mg", efficacy_text="세균 감염을 치료하는 약입니다.")
    assert r.efficacy is None
    assert "효능 문장" in r.reason


def test_efficacy_text_match_is_kept(index):
    r = find_by_name(index, "타이레놀정500mg", efficacy_text="열을 내리고 통증을 줄여 주는 약입니다.")
    assert r.efficacy is not None and r.efficacy.label == "해열진통제"


def test_unknown_name(index):
    r = find_by_name(index, "없는약정10mg")
    assert r.efficacy is None


def test_ingredient_fallback(index):
    # 상표(뮤코펙트)는 없지만 괄호 속 성분(암브록솔)으로 찾는다
    r = find_by_name(index, "뮤코펙트시럽(암브록솔염산염)", unit="mL")
    assert r.efficacy == Efficacy("진해거담제", "name_lookup", "ingredient")


def test_class_name_used_when_number_unknown(index):
    r = find_by_name(index, "엘도스캡슐300mg", unit="캡슐")
    assert r.efficacy is not None and r.efficacy.label == "테스트분류"


# ------------------------------------------------------------------ OCR 오타


def test_typo_with_enough_evidence_is_fuzzy(index):
    # '맥'→'멕' 한 글자 오타. 제형·함량·단위·색이 모두 맞는다
    r = find_by_name(index, "지스로멕스정250mg", unit="정", chart="분홍색 장방형 필름코팅정")
    assert r.efficacy == Efficacy("항생제", "name_lookup", "fuzzy")


def test_typo_without_evidence_is_rejected(index):
    # 오타인데 제형·함량 정보가 없어 후보가 여러 개 남는다
    r = find_by_name(index, "지스로멕스")
    assert r.efficacy is None
    assert "근거가 부족" in r.reason


def test_short_name_typo_is_not_guessed(index):
    # 너무 짧은 이름은 한 글자 차이로 엉뚱한 약과 이어질 수 있어 오타로 보지 않는다
    assert find_by_name(index, "타이레늘정").efficacy is None


# ------------------------------------------------------------------ 보험코드·전체 순서


def test_insurance_code(index):
    assert find_by_insurance_code(index, "600000001") == Efficacy("항생제", "insurance_code", "code")
    assert find_by_insurance_code(index, "123456789") is None
    assert find_by_insurance_code(index, None) is None


def test_printed_class_comes_first(index):
    # 약봉투 분류가 있으면 조회하지 않고 그대로 쓴다
    med = {"name": "헷갈림정", "printed_class": "[해열진통제]"}
    assert efficacy_for(med, index) == Efficacy("해열진통제", "pharmacy_bag", "printed")


def test_insurance_code_before_name(index):
    med = {"name": "헷갈림정", "insurance_code": "600000005"}
    assert efficacy_for(med, index) == Efficacy("진해거담제", "insurance_code", "code")


def test_name_lookup_last(index):
    med = {"name": "시네츄라시럽", "unit": "mL", "efficacy_text": "기침을 가라앉히고 가래 배출을 돕는 약입니다."}
    assert efficacy_for(med, index) == Efficacy("진해거담제", "name_lookup", "exact")


def test_no_index_only_printed(index):
    assert efficacy_for({"name": "타이레놀정500mg"}, None) is None
    assert efficacy_for({"name": "x", "printed_class": "항생제"}, None) == Efficacy("항생제", "pharmacy_bag", "printed")


def test_as_dict_shape():
    assert Efficacy("항생제", "name_lookup", "exact").as_dict() == {
        "label": "항생제",
        "source": "name_lookup",
        "match": "exact",
    }


# ------------------------------------------------------------------ 파일 읽기


def test_load_records_cp949(tmp_path):
    path = tmp_path / "drugs.csv"
    text = "ITEM_NAME,CLASS_NO,ITEM_INGR_NAME,EDI_CODE,CHART\n시네츄라시럽,222,,600000005,갈색 시럽\n,114,,,\n"
    path.write_bytes(text.encode("cp949"))
    records = load_records(path)
    assert len(records) == 1  # 품목명이 빈 줄은 건너뛴다
    assert records[0].item_name == "시네츄라시럽" and records[0].label == "진해거담제"


@pytest.mark.parametrize(
    ("class_no", "class_name", "label"),
    [
        ("222", None, "진해거담제"),
        ("[02220]진해거담제", None, "진해거담제"),  # 번호에 이름이 붙어 오는 경우
        ("06180", None, "항생제"),  # 앞의 0을 떼고 61x
        ("[09990]테스트분류", None, "테스트분류"),  # 표에 없으면 붙어 온 이름
        ("999", "[999]테스트분류", "테스트분류"),
        (None, None, None),
    ],
)
def test_class_label(class_no, class_name, label):
    assert class_label(class_no, class_name) == label


def test_get_drug_index_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(drug_lookup, "DRUG_DATA_PATH", tmp_path / "없음.csv")
    drug_lookup.get_drug_index.cache_clear()
    try:
        assert drug_lookup.get_drug_index() is None
    finally:
        drug_lookup.get_drug_index.cache_clear()


def test_get_drug_index_reads_once(tmp_path, monkeypatch):
    path = tmp_path / "drugs.csv"
    path.write_text("ITEM_NAME,CLASS_NO\n시네츄라시럽,222\n", encoding="utf-8")
    monkeypatch.setattr(drug_lookup, "DRUG_DATA_PATH", path)
    drug_lookup.get_drug_index.cache_clear()
    try:
        first = drug_lookup.get_drug_index()
        assert first is not None and first.size == 1
        assert drug_lookup.get_drug_index() is first
    finally:
        drug_lookup.get_drug_index.cache_clear()


# ------------------------------------------------------------------ ATC 코드 (식약처 허가 상세정보)


@pytest.mark.parametrize(
    ("atc", "label"),
    [
        ("J01FA10", "항생제"),  # 아지트로마이신
        ("N02BE01", "해열진통제"),  # 아세트아미노펜
        ("M01AE01", "해열진통소염제"),  # 이부프로펜
        ("R05CB06", "거담제"),  # 암브록솔
        ("A01AB03", "구강소독제"),  # 클로르헥시딘
        ("R02AA05", "인후소독제"),  # 헥사메딘액 (실제 허가정보 값)
        ("J01FA10, J01FA10", "항생제"),
        ("J01FA10,N02BE01", None),  # 코드가 서로 다른 분류면 쓰지 않는다
        ("Z99XX01", None),  # 표에 없는 코드는 짐작하지 않는다
        ("", None),
        (None, None),
    ],
)
def test_atc_label(atc, label):
    assert atc_label(atc) == label


def test_atc_comes_before_class_no():
    r = DrugRecord("테스트정", class_no="114", atc_code="J01FA10")
    assert r.label == "항생제"


def test_real_api_row_shape():
    # 식약처 허가 상세정보 응답 그대로의 모양 (try_mfds 결과)
    r = DrugRecord(
        "지스로맥스정250밀리그람(아지트로마이신수화물)",
        ingredient="[M250781]아지트로마이신수화물",
        edi_code="648900880",
        atc_code="J01FA10",
    )
    idx = DrugIndex(
        [r, DrugRecord("지스로맥스건조시럽(아지트로마이신수화물)", edi_code="648900871,648900872", atc_code="J01FA10")]
    )
    assert r.parsed.stem == "지스로맥스" and r.parsed.strength == "250mg"
    assert find_by_insurance_code(idx, "648900872") == Efficacy("항생제", "insurance_code", "code")
    assert find_by_name(idx, "지스로맥스정250mg", unit="정").efficacy == Efficacy("항생제", "name_lookup", "exact")
    # 성분 앞의 [M250781] 코드는 떼고 비교한다
    assert find_by_name(idx, "다른이름정(아지트로마이신)").efficacy is not None


def test_load_records_api_columns(tmp_path):
    path = tmp_path / "drugs.csv"
    path.write_text(
        "ITEM_NAME,MAIN_ITEM_INGR,EDI_CODE,CHART,ATC_CODE\n"
        "지스로맥스정250밀리그람(아지트로마이신수화물),[M250781]아지트로마이신수화물,"
        "648900880,분홍색 장방형 필름코팅정,J01FA10\n",
        encoding="utf-8-sig",
    )
    (record,) = load_records(path)
    assert record.label == "항생제" and record.edi_code == "648900880"


def test_load_records_multiline_field(tmp_path):
    # 성상 칸 안에 줄바꿈이 있어도 한 품목으로 읽는다 (실제 허가정보에 있음)
    path = tmp_path / "drugs.csv"
    path.write_text(
        "ITEM_NAME,CHART,ATC_CODE\n"
        '대한멸균증류수(주사용수),"무색투명한 액을 충진한\n플라스틱제 용기",V07AB\n'
        "시네츄라시럽,갈색,R05\n",
        encoding="utf-8-sig",
    )
    records = load_records(path)
    assert [r.item_name for r in records] == ["대한멸균증류수(주사용수)", "시네츄라시럽"]


def test_hexamedine_real_row():
    idx = DrugIndex([DrugRecord("헥사메딘액0.12%(클로르헥시딘글루콘산염액)", atc_code="R02AA05")])
    r = find_by_name(idx, "헥사메딘액0.12%", unit="mL", efficacy_text="목 안을 소독하는 가글액입니다.")
    assert r.efficacy == Efficacy("인후소독제", "name_lookup", "exact")


def test_unknown_atc_reason_names_the_code():
    idx = DrugIndex([DrugRecord("모르는약정", atc_code="Z99XX01")])
    r = find_by_name(idx, "모르는약정")
    assert r.efficacy is None and "Z99XX01" in r.reason
