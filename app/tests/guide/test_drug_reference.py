"""가이드 약 정보(reference) 찾기 — app/services/guide/drug_reference.py

API 서버 이미지(app/Dockerfile)에는 app/ 폴더만 들어간다. 예전에는 코드·데이터가 ai_worker/에 있어서
서버에서는 import가 실패하고 모든 약이 '참조 정보 없음'이 됐다. 그 일이 다시 생기지 않게 확인한다.
"""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.guide import drug_reference
from app.services.guide.drug_reference import DrugRefIndex, build_references_with_report, summarize
from app.services.guide.permit_ingredient_index import PermitIngredientIndex, PermitItem, ingredient_set
from app.services.guide.service import normalize_medication, references_for
from app.services.prescriptions import guide_inputs

APP_DIR = Path(drug_reference.__file__).resolve().parents[2]  # app/


def test_data_file_is_inside_app_folder():
    """서버 이미지에 함께 들어가려면 데이터가 app/ 안에 있어야 한다."""
    assert drug_reference.DEFAULT_PATH.is_relative_to(APP_DIR)
    assert drug_reference.DEFAULT_PATH.exists()
    assert len(DrugRefIndex().drugs) >= 21


def test_reviewed_drug_gets_reference_by_name():
    refs = references_for([normalize_medication({"medication_id": 1, "name": "비오플250산"})])
    assert refs[1].startswith("[출처: 식약처")
    assert "효능:" in refs[1]
    assert "같은 성분의 다른 제품" not in refs[1]


def test_same_ingredient_product_is_marked():
    """세토펜현탁액은 검수 문서가 없지만 같은 성분(아세트아미노펜) 문서를 쓰고, 그렇다고 표시한다."""
    meds = [normalize_medication({"medication_id": 7, "name": "세토펜현탁액(아세트아미노펜)/100(1)mL/병"})]
    refs, report = build_references_with_report(meds)
    assert report[0].method == "permit_ingredient"  # 허가 CSV로 성분이 같다고 확인함
    assert "같은 성분의 다른 제품 정보" in refs[7]


def test_unknown_drug_is_left_out():
    refs = references_for([normalize_medication({"medication_id": 3, "name": "포리부틴드라이시럽"})])
    assert refs == {}


def test_missing_data_file_warns_and_finds_nothing(tmp_path):
    with patch.object(drug_reference.logger, "warning") as warn:
        index = DrugRefIndex(tmp_path / "없음.json")
    assert index.drugs == []
    warn.assert_called_once()


# ------------------------------------------------------------------ 허가 CSV 성분으로 연결하기


def _doc(key, item_seq, forms, status="done", **extra):
    return {
        "key": key,
        "names": [key],
        "ingredient": extra.pop("ingredient", ""),
        "dosage_forms": forms,
        "item_seq": item_seq,
        "efficacy": f"{key} 효능",
        "cautions": f"{key} 주의",
        "source": {"name": "시험"},
        "status": status,
        **extra,
    }


@pytest.fixture
def ref_index(tmp_path):
    docs = [
        _doc("챔프시럽", "11", ["시럽"]),
        _doc("챔프정", "12", ["정제"]),
        _doc("락티케어로션", "21", ["로션"], ingredient="hydrocortisone"),
        _doc("토브렉스점안액", "31", ["점안액"]),
        _doc("검수전시럽", "41", ["시럽"], status="review"),
        _doc("코대원에스시럽", "51", ["시럽"], dur_age_taboo="12세 미만 소아 금기"),
    ]
    path = tmp_path / "drug_refs.json"
    path.write_text(json.dumps({"drugs": docs}, ensure_ascii=False), encoding="utf-8")
    permit = PermitIngredientIndex(
        [
            PermitItem("11", "챔프시럽(아세트아미노펜)", ingredient_set("[M040353]아세트아미노펜"), ("111111111",)),
            PermitItem("12", "챔프정(아세트아미노펜)", ingredient_set("[M040353]아세트아미노펜"), ()),
            PermitItem("13", "세토펜현탁액(아세트아미노펜)", ingredient_set("[M040353]아세트아미노펜"), ()),
            PermitItem("21", "락티케어로션(히드로코르티손)", ingredient_set("[M040818]히드로코르티손"), ()),
            PermitItem(
                "22", "로코이드크림(히드로코르티손부티레이트)", ingredient_set("[M1]히드로코르티손부티레이트"), ()
            ),
            PermitItem("31", "토브렉스점안액(토브라마이신)", ingredient_set("[M020144]토브라마이신"), ()),
            PermitItem("32", "토브라마이신주사(토브라마이신)", ingredient_set("[M020144]토브라마이신"), ()),
            PermitItem("41", "검수전시럽(돔페리돈)", ingredient_set("[M2]돔페리돈"), ()),
            PermitItem("42", "대원돔페리돈현탁액", ingredient_set("[M2]돔페리돈"), ()),
        ]
    )
    return DrugRefIndex(path, permit=permit)


def test_same_ingredient_by_permit_data(ref_index):
    doc, m = ref_index.find({"medication_id": 1, "name": "세토펜현탁액", "dosage_form": "시럽"})
    assert (m.method, doc["key"]) == ("permit_ingredient", "챔프시럽")


def test_same_ingredient_prefers_same_dosage_form(ref_index):
    doc, _ = ref_index.find({"medication_id": 1, "name": "세토펜현탁액", "dosage_form": "정제"})
    assert doc["key"] == "챔프정"


def test_insurance_code_of_reviewed_product(ref_index):
    doc, m = ref_index.find({"medication_id": 1, "name": "모르는 이름", "insurance_code": "111111111"})
    assert (m.method, doc["key"]) == ("insurance", "챔프시럽")


def test_different_ingredient_is_not_linked_even_if_ingredient_table_says_so(ref_index):
    """성분 표가 예전처럼 'hydrocortisone'이라고 해도 허가 데이터상 성분이 다르면 연결하지 않는다."""
    med = {"medication_id": 1, "name": "로코이드크림(히드로코르티손부티레이트)", "ingredient": "hydrocortisone"}
    doc, m = ref_index.find(med)
    assert doc is None and m.method == "none"


def test_eye_drop_document_is_not_used_for_other_route(ref_index):
    med = {"medication_id": 1, "name": "토브라마이신주사(토브라마이신)", "route": "내복"}
    assert ref_index.find(med)[0] is None
    med["route"] = "외용"
    assert ref_index.find(med)[0]["key"] == "토브렉스점안액"


def test_review_status_document_is_not_used(ref_index):
    assert ref_index.find({"medication_id": 1, "name": "대원돔페리돈현탁액"})[0] is None


def test_summary_includes_dur_age_taboo(ref_index):
    doc, _ = ref_index.find({"medication_id": 1, "name": "코대원에스시럽"})
    assert "연령 금기(DUR): 12세 미만 소아 금기" in summarize(doc)


def test_guide_inputs_pass_insurance_code():
    med = SimpleNamespace(
        id=1, name="세토펜현탁액", insurance_code="649806731", dose_per_time=5, unit="mL", daily_count=3,
        total_days=3, as_needed=False, max_daily_count=None, usage="식후", route=None, dosage_form=None,
    )  # fmt: skip
    child = SimpleNamespace(birth_date=date(2024, 1, 1), weight_kg=None, allergies=None)
    rx = SimpleNamespace(
        id=1, prescription_date=None, hospital_name=None, diagnosis_user_input=None, symptom_notes=None
    )
    _, _, meds = guide_inputs(child, rx, [med])
    assert meds[0]["insurance_code"] == "649806731"
