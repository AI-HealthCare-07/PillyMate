import pytest

from ocr.ocr_confidence_policy import OK, RETAKE, REVIEW, is_low_confidence, judge_ocr_confidence


def result_with(*confidences):
    return {"medications": [{"name": f"약{i}", "confidence": value} for i, value in enumerate(confidences)]}


@pytest.mark.parametrize(
    ("confidences", "level"),
    [
        ((0.95, 0.8), OK),
        ((1.0,), OK),
        ((0.95, 0.79), REVIEW),
        ((0.6, 0.99), REVIEW),
        ((0.95, 0.59), RETAKE),
        ((0.3,), RETAKE),
    ],
)
def test_lowest_medication_decides_the_level(confidences, level):
    assert judge_ocr_confidence(result_with(*confidences))["level"] == level


def test_no_medications_means_retake():
    judged = judge_ocr_confidence({"medications": []})

    assert judged == {"level": RETAKE, "min_confidence": None, "low_confidence_count": 0}


def test_unknown_confidence_is_ignored_and_all_unknown_needs_review():
    assert judge_ocr_confidence(result_with(None, 0.9))["level"] == OK
    assert judge_ocr_confidence(result_with(None, None))["level"] == REVIEW


def test_reports_lowest_value_and_how_many_to_highlight():
    judged = judge_ocr_confidence(result_with(0.95, 0.7, 0.65))

    assert judged == {"level": REVIEW, "min_confidence": 0.65, "low_confidence_count": 2}


def test_low_confidence_highlight_threshold():
    assert is_low_confidence(0.79)
    assert not is_low_confidence(0.8)
    assert not is_low_confidence(None)
