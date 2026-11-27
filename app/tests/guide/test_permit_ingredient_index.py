"""허가정보 CSV로 처방 약의 성분 찾기 — app/services/guide/permit_ingredient_index.py"""

import pytest

from app.services.guide import permit_ingredient_index as pii
from app.services.guide.permit_ingredient_index import PermitIngredientIndex, PermitItem, ingredient_set


@pytest.mark.parametrize(
    ("main_item_ingr", "expected"),
    [
        ("[M245961]클래리트로마이신제피과립", {"클래리트로마이신"}),  # 원료 모양은 같은 성분
        ("[M256483]클래리트로마이신제피과립(42%)", {"클래리트로마이신"}),
        ("[M085725]클래리스로마이신", {"클래리트로마이신"}),  # 다른 한글 표기
        ("[M222859]세파클러수화물", {"세파클러"}),  # 염·수화물은 같은 성분
        ("[M051285]염산세티리진", {"세티리진"}),
        ("[M020145]황산토브라마이신", {"토브라마이신"}),
        ("[M1]인산오셀타미비르", {"오셀타미비르"}),
        ("[M1]모메타손푸로에이트일수화물", {"모메타손푸로에이트"}),
        ("[M281939]아세트아미노펜(미분화)", {"아세트아미노펜"}),
        ("[M223098]아목시실린수화물|[M248503]묽은클라불란산칼륨", {"아목시실린", "클라불란산"}),
        ("[M096290]아목시실린ㆍ클라불란산칼륨(4:1)", {"아목시실린", "클라불란산"}),  # 한 칸의 복합 성분
    ],
)
def test_same_ingredient_written_differently(main_item_ingr, expected):
    assert ingredient_set(main_item_ingr) == frozenset(expected)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("[M084591]낙산히드로코르티손", "[M040818]히드로코르티손"),  # 에스테르는 다른 성분
        ("[M1]히드로코르티손부티레이트", "[M040818]히드로코르티손"),
        ("[M244596]레보세티리진염산염", "[M222857]세티리진염산염"),
        ("[M092184]아세브로필린(아세필린산암브록솔)", "[M233843]암브록솔염산염"),
    ],
)
def test_different_ingredients_stay_different(a, b):
    assert ingredient_set(a) != ingredient_set(b)


def _item(seq, name, ingr, edi=()):
    return PermitItem(seq, name, ingredient_set(ingr), tuple(edi))


@pytest.fixture
def index():
    return PermitIngredientIndex(
        [
            _item("1", "세토펜현탁액(아세트아미노펜)", "[M040353]아세트아미노펜", ["649806731"]),
            _item("2", "소론도정(프레드니솔론)", "[M1]프레드니솔론"),
            _item("3", "대원돔페리돈현탁액", "[M2]돔페리돈"),
            _item("4", "한미돔페리돈현탁액", "[M2]돔페리돈"),
            _item("5", "복합써스펜좌약", "[M040353]아세트아미노펜|[M223015]DL-메티오닌"),
            _item("6", "코푸시럽", "[M3]디히드로코데인타르타르산염|[M4]클로르페니라민말레산염"),
            _item("7", "코푸시럽", "[M3]디히드로코데인타르타르산염"),  # 같은 이름, 다른 성분
            _item("8", "몬테루카스트츄정(몬테루카스트나트륨)", "[M5]몬테루카스트나트륨"),
            _item("9", "씨잘정5밀리그램(레보세티리진염산염)", "[M244596]레보세티리진염산염"),
            _item("10", "씨잘액(레보세티리진염산염)", "[M244596]레보세티리진염산염"),
            _item("11", "같은상표정", "[M6]성분가"),
            _item("12", "같은상표액", "[M7]성분나"),
        ]
    )


def test_finds_by_insurance_code_first(index):
    ingredients, _, how = index.lookup({"name": "아무 이름", "insurance_code": "649806731"})
    assert (ingredients, how) == (frozenset({"아세트아미노펜"}), "code")


def test_finds_by_exact_name_with_unit_words(index):
    ingredients, _, how = index.lookup({"name": "소론도정5밀리그램(프레드니솔론)/1정"})
    assert (ingredients, how) == (frozenset({"프레드니솔론"}), "name")


def test_uses_ingredient_written_in_brackets(index):
    ingredients, _, how = index.lookup({"name": "싱귤레어츄정5밀리그램(몬테루카스트나트륨)/1정"})
    assert (ingredients, how) == (frozenset({"몬테루카스트"}), "bracket")


def test_ignores_bracket_text_that_is_not_a_known_ingredient(index):
    assert index.ingredients_for({"name": "세티리진시럽1mg/mL(내복)/100(1)mL/병"}) is None
    assert index.ingredients_for({"name": "비오플250산(사카로아이세스보울라디)"}) is None  # OCR 오타


def test_finds_product_with_company_prefix(index):
    ingredients, items, how = index.lookup({"name": "돔페리돈현탁액"})
    assert (ingredients, how) == (frozenset({"돔페리돈"}), "contains")
    assert len(items) == 2


def test_combination_prefix_is_not_the_same_drug(index):
    """'써스펜좌약'을 '복합써스펜좌약'(아세트아미노펜+메티오닌)으로 보면 안 된다."""
    assert index.ingredients_for({"name": "써스펜좌약125mg"}) is None


def test_candidates_with_different_ingredients_give_none(index):
    assert index.ingredients_for({"name": "코푸시럽(내복)/100(1)mL/병"}) is None


def test_missing_csv_gives_empty_index(tmp_path, monkeypatch):
    monkeypatch.setattr(pii, "DRUG_DATA_PATH", tmp_path / "없음.csv")
    pii.default_permit_index.cache_clear()
    try:
        assert len(pii.default_permit_index()) == 0
    finally:
        pii.default_permit_index.cache_clear()


def test_finds_by_brand_stem_when_name_is_not_registered(index):
    """허가 데이터에 '씨잘시럽'은 없고 씨잘정·씨잘액만 있다. 상표 '씨잘'의 성분이 모두 같으니 그 성분."""
    ingredients, items, how = index.lookup({"name": "씨잘시럽"})
    assert (ingredients, how) == (frozenset({"레보세티리진"}), "stem")
    assert {it.item_seq for it in items} == {"9", "10"}


def test_brand_stem_with_different_ingredients_gives_none(index):
    assert index.ingredients_for({"name": "같은상표시럽"}) is None


def test_representative_prefers_same_form_family():
    from app.services.guide.permit_ingredient_index import representative_item

    tablet = _item("9", "씨잘정5밀리그램(레보세티리진염산염)", "[M244596]레보세티리진염산염")
    liquid = _item("10", "씨잘액(레보세티리진염산염)", "[M244596]레보세티리진염산염")
    other = _item("13", "다른회사레보세티리진시럽", "[M244596]레보세티리진염산염")
    picked = representative_item([tablet, other, liquid], tablet.ingredients, "씨잘시럽")
    assert picked.item_seq == "10"  # 같은 상표 + 같은 물약 묶음이 다른 회사 시럽보다 먼저
