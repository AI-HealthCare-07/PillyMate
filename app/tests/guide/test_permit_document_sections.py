"""허가 문서 XML에서 초안에 쓸 단락 고르기 — app/services/guide/permit_document_sections.py"""

from app.services.guide.permit_document_sections import (
    articles,
    category_of,
    caution_sections,
    efficacy_text,
    permit_document,
)

NB = """<DOC title="사용상의주의사항" type="NB"><SECTION title="">
<ARTICLE title="1. 경고"><PARAGRAPH><![CDATA[12세 미만 소아에게 투여하지 않는다.]]></PARAGRAPH></ARTICLE>
<ARTICLE title="2. 다음 환자에는 투여하지 말 것"><PARAGRAPH><![CDATA[1) 과민증 환자]]></PARAGRAPH>
<PARAGRAPH><![CDATA[2) 2세 미만]]></PARAGRAPH></ARTICLE>
<ARTICLE title="3. 이상반응"><PARAGRAPH><![CDATA[졸음, 입마름]]></PARAGRAPH></ARTICLE>
<ARTICLE title="4. 상호작용"><PARAGRAPH><![CDATA[MAO 억제제와 병용 금지]]></PARAGRAPH></ARTICLE>
<ARTICLE title="5. 임부 및 수유부에 대한 투여"><PARAGRAPH><![CDATA[임부에게 투여하지 않는다.]]></PARAGRAPH></ARTICLE>
<ARTICLE title="6. 소아에 대한 투여"><PARAGRAPH><![CDATA[안전성이 확립되지 않았다.]]></PARAGRAPH></ARTICLE>
<ARTICLE title="7. 보관 및 취급상의 주의사항"><PARAGRAPH><![CDATA[어린이의 손이 닿지 않는 곳에 보관한다.]]></PARAGRAPH></ARTICLE>
</SECTION></DOC>"""
EE = """<DOC title="효능효과" type="EE"><SECTION title="">
<ARTICLE title="1. 두드러기" /><ARTICLE title="2. 피부 가려움" /></SECTION></DOC>"""


def test_articles_reads_cdata_paragraphs():
    arts = articles(NB)
    assert arts[1] == ("2. 다음 환자에는 투여하지 말 것", "1) 과민증 환자 2) 2세 미만")


def test_articles_of_broken_or_empty_xml_is_empty():
    assert articles("<DOC>") == []
    assert articles(None) == []


def test_category_of_titles():
    assert category_of("2. 다음 환자에는 투여하지 말 것") == "contraindication"
    assert category_of("다음과 같은 사람은 이 약을 복용하지 말 것") == "contraindication"  # 일반의약품 문서
    assert category_of("8. 소아에 대한 투여") == "child"
    assert category_of("6. 상호작용") is None
    assert category_of("7. 임부 및 수유부에 대한 투여") is None


def test_caution_sections_keep_only_needed_parts():
    sections = caution_sections(NB)
    assert set(sections) == {"warning", "contraindication", "side_effects", "child", "storage"}
    assert "MAO" not in " ".join(sections.values())
    assert "임부" not in " ".join(sections.values())


def test_efficacy_from_article_titles():
    assert efficacy_text(EE) == "1. 두드러기 2. 피부 가려움"


def test_permit_document_from_api_item():
    doc = permit_document(
        {"ITEM_SEQ": 1, "ITEM_NAME": " 시험시럽 ", "EE_DOC_DATA": EE, "NB_DOC_DATA": NB, "STORAGE_METHOD": "실온"}
    )
    assert (doc.item_seq, doc.item_name, doc.storage_method) == ("1", "시험시럽", "실온")
    assert not doc.is_empty()
    assert permit_document({"ITEM_SEQ": 2}).is_empty()


def test_html_tags_inside_cdata_are_removed():
    xml = '<DOC><SECTION><ARTICLE title="1. 효능"><PARAGRAPH><![CDATA[식도역류<sub>,</sub> 위염]]></PARAGRAPH></ARTICLE></SECTION></DOC>'
    assert articles(xml) == [("1. 효능", "식도역류, 위염")]


def test_long_sections_are_not_cut():
    """이상반응은 앞부분이 임상시험 통계라 앞에서 자르면 흔한 부작용이 빠진다 → 자르지 않는다."""
    body = "가" * 5000 + " 흔한 부작용: 구토"
    xml = f'<DOC><SECTION><ARTICLE title="4. 이상반응"><PARAGRAPH><![CDATA[{body}]]></PARAGRAPH></ARTICLE></SECTION></DOC>'
    assert caution_sections(xml)["side_effects"].endswith("흔한 부작용: 구토")
