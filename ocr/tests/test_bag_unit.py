from ocr.ocr_result_formatter import bag_unit


def test_bag_unit_not_allowed_is_not_guessed():
    # 약봉투에 '앰플'이라고 적혀 있으면 이름의 '/2mL'로 바꾸지 않는다
    assert bag_unit("앰플", "풀미코트레스퓰0.5mg/2mL", None) is None
    assert bag_unit("흡입", "벤토린에보할러", "ETC") is None


def test_bag_unit_allowed_is_kept():
    assert bag_unit("mL", "세파클러건조시럽", "DRY_SYRUP") == "mL"


def test_bag_unit_missing_is_guessed():
    # 단위 칸이 비었을 때만 짐작한다
    assert bag_unit(None, "세파클러건조시럽", "DRY_SYRUP") == "mL"
    assert bag_unit("  ", "타이레놀정500mg", "TABLET") == "정"