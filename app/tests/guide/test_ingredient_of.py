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
