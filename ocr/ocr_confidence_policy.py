"""run_ocr() 결과의 신뢰도로 다음 단계를 정한다 (11/24 멘토링 3절 기준).

| 가장 낮은 약 신뢰도 | 판정     | 다음 단계                                   |
| ------------------- | -------- | ------------------------------------------- |
| 0.80 이상           | `OK`     | 인식 결과 확인 (S-04)                       |
| 0.60 이상 ~ 0.80 미만 | `REVIEW` | S-04에서 신뢰도 낮은 약을 강조해 직접 수정  |
| 0.60 미만           | `RETAKE` | 저장하지 않고 다시 찍기                     |

- 판정 단위는 약 한 줄이다. 약이 여러 개면 가장 낮은 신뢰도로 사진 전체를 판정한다.
  흐릿한 부분이 한 곳이라도 있으면 그 부분은 직접 고치거나 다시 찍어야 하기 때문이다.
- 약을 하나도 읽지 못했으면 고칠 거리가 없으니 `RETAKE`다.
- 신뢰도가 없는 약(None)은 판정에서 뺀다. 모든 약이 None이면 `REVIEW`로 보내 보호자가 확인하게 한다.
- 기준값은 "실제 테스트 후 확정"(멘토링 회의록)이라 바꾸기 쉽게 상수로 둔다.
"""

OK = "OK"
REVIEW = "REVIEW"
RETAKE = "RETAKE"

RETAKE_BELOW = 0.6
REVIEW_BELOW = 0.8


def is_low_confidence(confidence):
    """S-04에서 강조할 약인지. 신뢰도를 모르면 강조하지 않는다."""
    return confidence is not None and confidence < REVIEW_BELOW


def judge_ocr_confidence(result):
    """run_ocr() 결과 → {"level", "min_confidence", "low_confidence_count"}."""
    medications = result.get("medications") or []
    confidences = [m["confidence"] for m in medications if m.get("confidence") is not None]
    min_confidence = min(confidences) if confidences else None
    low_count = sum(1 for value in confidences if is_low_confidence(value))

    if not medications or (min_confidence is not None and min_confidence < RETAKE_BELOW):
        level = RETAKE
    elif min_confidence is None or low_count:
        level = REVIEW
    else:
        level = OK
    return {"level": level, "min_confidence": min_confidence, "low_confidence_count": low_count}
