"""e약은요 응답에서 초안에 쓸 칸 고르기 — app/services/guide/easy_drug_info_fields.py"""

from app.services.guide.easy_drug_info_fields import easy_drug_info


def test_keeps_needed_fields_and_drops_dosing():
    info = easy_drug_info(
        {
            "itemSeq": 197900171,
            "itemName": "후시딘연고(퓨시드산나트륨)",
            "efcyQesitm": "<p>이 약은 &lt;농가진&gt;에 사용합니다.</p>",
            "useMethodQesitm": "1일 1~2회 바릅니다.",  # 용량 — 쓰지 않음
            "intrcQesitm": "다른 약과 함께",  # 상호작용 — 쓰지 않음
            "atpnWarnQesitm": None,
            "atpnQesitm": "과민증 환자는  사용하지 마십시오.",
            "seQesitm": "가려움, 발적",
            "depositMethodQesitm": "실온에서 보관하십시오.",
        }
    )
    assert (info.item_seq, info.item_name) == ("197900171", "후시딘연고(퓨시드산나트륨)")
    assert info.sections == {
        "효능": "이 약은 <농가진>에 사용합니다.",
        "주의": "과민증 환자는 사용하지 마십시오.",
        "부작용": "가려움, 발적",
        "보관": "실온에서 보관하십시오.",
    }
    assert "1~2회" not in " ".join(info.sections.values())


def test_empty_item_is_empty():
    assert easy_drug_info({"itemSeq": "1"}).is_empty()
