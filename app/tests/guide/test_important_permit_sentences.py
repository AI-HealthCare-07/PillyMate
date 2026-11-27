"""허가 문서 단락에서 중요한 문장 고르기 — app/services/guide/important_permit_sentences.py"""

from app.services.guide.important_permit_sentences import pick_important, units

SIDE_EFFECTS = (
    "4. 이상반응: 인플루엔자에 감염된 2,646명 이상의 성인 및 859명 이상의 소아 환자의 임상시험 결과를 바탕으로 "
    "이 약의 전체적인 안전성을 평가하였다. 성인에 대한 치료연구 중 가장 빈번하게 보고된 약물이상반응은 구역, 구토 및 "
    "두통이었다. 소아에서 가장 빈번하게 보고된 약물이상반응은 구토였다. 아래 표 1에 나열하였다."
)


def test_common_side_effects_come_before_trial_statistics():
    picked = pick_important(SIDE_EFFECTS, 120, "side_effects")
    assert "소아에서 가장 빈번하게 보고된 약물이상반응은 구토였다." in picked
    assert "2,646명" not in picked
    assert "표 1" not in picked


def test_sentences_with_dose_numbers_are_dropped():
    text = (
        "8. 소아에 대한 투여: 1세 미만의 소아에 대한 유효성이 확립되어 있지 않다. 소아에게 3mg/kg을 1일 2회 투여하였다."
    )
    picked = pick_important(text, 200)
    assert picked == "1세 미만의 소아에 대한 유효성이 확립되어 있지 않다."


def test_original_order_is_kept_and_title_removed():
    text = "2. 다음 환자에는 투여하지 말 것: 1) 과민반응 환자 2) 12세 미만의 소아"
    assert pick_important(text, 200) == "1) 과민반응 환자 2) 12세 미만의 소아"


def test_units_split_numbered_items_and_drop_repeats():
    text = "3. 이상반응: ① 쇼크 : 청색증 ② 과민반응 : 발진 1) 변화가 없었다. 변화가 없었다. 변화가 없었다."
    assert units(text) == ["① 쇼크 : 청색증", "② 과민반응 : 발진", "1) 변화가 없었다.", "변화가 없었다."]


def test_sentence_ending_with_geot_is_not_split():
    """'…투여할 것.'의 '것.'을 '가. 나.' 항목 기호로 보고 자르지 않는다."""
    text = "1) 1세 미만의 영아에게 투여해서는 안되고, 6세 미만의 유아에게는 액제를 투여할 것. 2) 과민증 환자"
    assert "액제를 투여할 것." in pick_important(text, 200)
