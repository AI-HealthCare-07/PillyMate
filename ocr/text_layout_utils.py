"""CLOVA OCR 글자 상자를 좌표로 다루는 공통 도구.

OCR 글자 순서는 표 칸 순서와 다르게 섞일 수 있어서 텍스트 순서 대신 좌표를 쓴다.
1. 사진이 기울어져 있으면 글자 기울기의 중앙값만큼 좌표를 되돌린다.
2. 높이가 비슷한 글자를 왼쪽부터 이어 붙여 '행'을 만든다.
처방전·약봉투 파서가 이 행을 보고 라벨 오른쪽 칸, 표 머리글 아래 칸 같은 위치로 값을 찾는다.
"""

import math
import re
from statistics import mean, median


class Box:
    """CLOVA 글자 상자 하나. 기울기를 되돌린 좌표와 인식 신뢰도를 가진다."""

    def __init__(self, field, angle):
        points = [(p.get("x", 0), p.get("y", 0)) for p in field["boundingPoly"]["vertices"]]
        cos, sin = math.cos(-angle), math.sin(-angle)
        points = [(x * cos - y * sin, x * sin + y * cos) for x, y in points]
        xs, ys = [x for x, _ in points], [y for _, y in points]
        self.text = field["inferText"].strip()
        self.confidence = field.get("inferConfidence")
        self.x0, self.x1, self.y0, self.y1 = min(xs), max(xs), min(ys), max(ys)
        self.cx, self.cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
        self.h = max(self.y1 - self.y0, 1)


def skew_angle(fields):
    """사진의 기울기 = CLOVA가 같은 줄로 본 이웃 단어들의 중심을 이은 선의 기울기 중앙값.

    CLOVA는 기울어진 사진에서도 단어 상자를 반듯한 직사각형으로 줄 때가 많아서
    상자 윗변보다 단어와 단어 사이의 높이 변화가 기울기를 더 잘 보여준다.
    """

    def center(field):
        v = field["boundingPoly"]["vertices"]
        return (
            sum(p.get("x", 0) for p in v) / len(v),
            sum(p.get("y", 0) for p in v) / len(v),
        )

    angles = []
    for field, following in zip(fields, fields[1:], strict=False):
        if field.get("lineBreak"):
            continue
        (x1, y1), (x2, y2) = center(field), center(following)
        if x2 - x1 > 20 and abs(y2 - y1) < 0.2 * (x2 - x1):
            angles.append(math.atan2(y2 - y1, x2 - x1))
    return median(angles) if angles else 0.0


def to_boxes(fields):
    """CLOVA fields를 기울기를 되돌린 Box 목록으로 바꾼다."""
    angle = skew_angle(fields)
    return [Box(field, angle) for field in fields]


def build_rows(boxes):
    """왼쪽부터 보면서 높이가 이어지는 상자끼리 같은 행으로 묶는다."""
    rows = []
    for box in sorted(boxes, key=lambda b: b.x0):
        best, best_gap = None, None
        for row in rows:
            last = row[-1]
            gap = abs(last.cy - box.cy)
            if gap < 0.6 * min(last.h, box.h) and (best_gap is None or gap < best_gap):
                best, best_gap = row, gap
        if best is None:
            rows.append([box])
        else:
            best.append(box)
    # OCR 상자가 겹칠 때(예: '28' 상자 안에 '월')는 왼쪽 끝보다 가운데 위치가 순서를 더 잘 나타낸다.
    rows = [sorted(row, key=lambda b: b.cx) for row in rows]
    return sorted(rows, key=lambda row: median(b.cy for b in row))


def compact(text):
    """공백을 모두 없앤 글자. 띄어 쓴 라벨('명  칭')을 비교할 때 쓴다."""
    return re.sub(r"\s+", "", text)


def to_number(text):
    return float(text) if "." in text else int(text)


def average_confidence(boxes):
    """상자들의 CLOVA 인식 신뢰도 평균(0~1). 신뢰도가 없으면 None."""
    values = [b.confidence for b in boxes if isinstance(b.confidence, int | float)]
    return round(mean(values), 2) if values else None
