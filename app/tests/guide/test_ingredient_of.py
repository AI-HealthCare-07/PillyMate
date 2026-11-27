import pytest

from app.services.guide.merge import ingredient_of


@pytest.mark.parametrize(
    ("name", "ingredient"),
    [
        ("아목시실린건조시럽", "amoxicillin"),
        ("오구멘틴듀오시럽", "amoxicillin/clavulanate"),
        ("오구엔틴정375밀리그(아목시실린·클라불란산칼륨)/1정", "amoxicillin/clavulanate"),
        ("크라맥스정625밀리그램(아목시실린·클라불란산칼륨)", "amoxicillin/clavulanate"),
    ],
)
def test_amoxicillin_single_vs_combination(name, ingredient):
    assert ingredient_of(name) == ingredient


@pytest.mark.parametrize(
    ("name", "ingredient"),
    [
        ("로코이드크림0.1%(히드로코르티손부티레이트)/20g/개", "hydrocortisone butyrate"),
        ("로코이드크림0.1%", "hydrocortisone butyrate"),
        ("락티케어에취씨로션1%(히드로코르티손)", "hydrocortisone"),
    ],
)
def test_hydrocortisone_butyrate_is_not_hydrocortisone(name, ingredient):
    """히드로코르티손부티레이트(로코이드)는 히드로코르티손보다 센 다른 성분이라 같은 약 정보를 붙이면 안 된다."""
    assert ingredient_of(name) == ingredient
