"""CLOVA OCR 결과를 약봉투 항목별 dict(한글 키)로 정리한다.

약봉투는 왼쪽 '약제비 계산서·영수증'과 오른쪽 '조제약 복약안내'가 나란히 있어서
같은 높이의 글자가 서로 섞이지 않도록 두 영역을 x 좌표로 먼저 나눈 뒤 각각 읽는다.
결과의 한글 키는 ocr_result_formatter가 API 명세 형식(snake_case)으로 바꾼다.
"""

import re

from ocr.text_layout_utils import average_confidence, build_rows, compact, to_boxes, to_number

MONEY = re.compile(r"([\d,]+)\s*원")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
DOSE = re.compile(r"(?:([\d.]+)\s*([^\d\s씩]+)씩|적당량)\s*(?:(\d+)\s*회\s*(\d+)\s*일분|(필요시))")
AGE = re.compile(r"만\s*(\d+)\s*세")


def row_text(row):
    return " ".join(box.text for box in row)


def after_label(rows, label):
    """행이 label로 시작하면 label 뒤의 글자를 돌려준다(띄어 쓴 라벨도 찾는다)."""
    for row in rows:
        joined = ""
        for i, box in enumerate(row):
            joined += compact(box.text)
            if not label.startswith(joined):
                break
            if joined == label:
                return row_text(row[i + 1 :]).strip() or None
            if len(joined) > len(label):
                break
    return None


def after_colon(rows, label):
    """'· 환자정보 : 김하윤' 처럼 '라벨 :' 뒤의 값(같은 행의 다음 라벨 전까지)."""
    for row in rows:
        for i, box in enumerate(row):
            if compact(box.text).rstrip(":") != label:
                continue
            values, previous = [], box
            for following in row[i + 1 :]:
                if values and following.x0 - previous.x1 > 3 * following.h:
                    break
                previous = following
                text = following.text.strip()
                if text in (":", "·", "."):
                    if values:
                        break
                    continue
                if text.endswith(":"):
                    break
                values.append(text)
            return " ".join(values) or None
    return None


def money(text):
    found = MONEY.search(text or "")
    return int(found.group(1).replace(",", "")) if found else None


def pattern(text, regex):
    found = regex.search(text or "")
    return found.group() if found else None


def split_panels(boxes):
    """복약안내 영역의 왼쪽 끝(약품사진 머리글이나 환자정보 라벨) 기준으로 나눈다."""
    anchors = [b for b in boxes if compact(b.text).rstrip(":") in ("약품사진", "환자정보", "교부번호", "병원정보")]
    right_anchors = [
        b for b in anchors if compact(b.text) != "교부번호" or ":" in b.text or b.x0 > min(a.x0 for a in anchors)
    ]
    if not right_anchors:
        return boxes, []
    split = min(b.x0 for b in right_anchors) - 30
    return [b for b in boxes if b.cx < split], [b for b in boxes if b.cx >= split]


def receipt_drugs(rows):
    """영수증 아래 '약품명 투약량 횟수 일수 총투' 표."""
    for r, row in enumerate(rows):
        headers = {compact(b.text): b for b in row}
        if {"약품명", "투약량", "횟수", "일수"} <= headers.keys():
            return read_receipt_table(rows[r + 1 :], headers)
    return []


def receipt_name_lines(lines, name_until):
    """약 이름 줄: 이름 칸에 글자가 있는 행. 빈 줄이 나오면 표가 끝난 것이다."""
    names = []
    for line in lines:
        parts = [b for b in line if b.x1 < name_until]
        if not parts:
            if names and not any(NUMBER.match(b.text) for b in line):
                break  # 숫자만 있는 줄은 위 약 이름의 값이므로 계속 본다.
            continue
        names.append(parts)
    if not names:
        return []
    gap = names[1][0].cy - names[0][0].cy if len(names) > 1 else 2 * names[0][0].h
    return [parts for parts in names if parts[0].cy - names[0][0].cy < gap * (len(names) + 0.5)]


def read_receipt_table(lines, headers):
    columns = [("투약량", headers["투약량"]), ("횟수", headers["횟수"]), ("일수", headers["일수"])]
    if "총투" in headers:
        columns.append(("총투", headers["총투"]))
    width = 0.6 * (headers["횟수"].cx - headers["투약량"].cx)
    names = receipt_name_lines(lines, headers["투약량"].x0)
    if not names:
        return []
    # receipt_name_lines가 거르기 전의 줄 간격과 같도록, 남은 첫 두 줄로 다시 잰다.
    gap = names[1][0].cy - names[0][0].cy if len(names) > 1 else 2 * names[0][0].h

    # 사진 일부만 기울어 있을 수 있어서, 머리글 줄의 기울기로 표 안의 높이를 보정한다.
    origin = headers["약품명"]
    tilt = (columns[-1][1].cy - origin.cy) / max(columns[-1][1].cx - origin.cx, 1)

    def level(box):
        return box.cy - tilt * (box.cx - origin.cx)

    # 숫자는 행으로 묶지 않고 높이가 가장 가까운 약 이름에 붙인다.
    # (이름 글자가 숫자보다 커서 사진에서는 같은 줄로 묶이지 않을 때가 있다.)
    items = [
        {
            "명칭": " ".join(b.text for b in parts),
            **{key: None for key, _ in columns},
            "신뢰도": average_confidence(parts),
        }
        for parts in names
    ]
    for box in (b for line in lines for b in line):
        if not NUMBER.match(box.text):
            continue
        column = next((key for key, header in columns if abs(box.cx - header.cx) < width), None)
        if not column:
            continue
        distances = [abs(level(box) - level(parts[0])) for parts in names]
        nearest = min(range(len(names)), key=distances.__getitem__)
        if distances[nearest] < 0.6 * gap and items[nearest][column] is None:
            items[nearest][column] = to_number(box.text)
    return [item for item in items if item["투약량"] is not None]


def receipt(rows):
    return {
        "영수증번호": after_label(rows, "영수증번호") and after_label(rows, "영수증번호").split()[0],
        "투약일수": int(found)
        if (found := pattern(after_label(rows, "영수증번호"), re.compile(r"(?<=투약일수 )\d+")))
        else None,
        "환자성명": after_label(rows, "환자성명"),
        "조제일자": pattern(after_label(rows, "조제일자"), DATE),
        "약제비총액": money(after_label(rows, "약제비총액")),
        "본인부담금": money(after_label(rows, "본인부담금")),
        "보험자부담금": money(after_label(rows, "보험자부담금")),
        "비급여": money(after_label(rows, "비급여(전액본인)")),
        "총수납금액": money(after_label(rows, "합계")),
        "사업자등록번호": pattern(after_label(rows, "사업자등록번호"), re.compile(r"\d{3}-\d{2}-\d{5}")),
        "사업장소재지": after_label(rows, "사업장소재지"),
        "상호": first_cell(rows, "상호"),
        "약사성명": first_cell(rows, "성명"),
        "발행일": pattern(after_label(rows, "발행일"), DATE),
        "약품내역": receipt_drugs(rows),
    }


def first_cell(rows, label):
    """label로 시작하는 행에서 바로 다음 칸 하나(도장 글자는 제외)."""
    for row in rows:
        joined = ""
        for i, box in enumerate(row):
            joined += compact(box.text)
            if joined == label and i + 1 < len(row):
                return row[i + 1].text
            if not label.startswith(joined):
                break
    return None


def parse_dose(text):
    found = DOSE.search(text or "")
    if not found:
        return {"1회용량": None, "단위": None, "1일횟수": None, "일수": None, "필요시": False}
    amount, unit, times, days, as_needed = found.groups()
    return {
        "1회용량": to_number(amount) if amount else "적당량",
        "단위": unit,
        "1일횟수": int(times) if times else None,
        "일수": int(days) if days else None,
        "필요시": bool(as_needed),
    }


def category_boxes(row):
    """'[항생제]' 또는 '[항생' '점안제]'처럼 나뉜 분류 글자 상자들."""
    for i, box in enumerate(row):
        if box.text.startswith("["):
            for j in range(i, len(row)):
                if row[j].text.endswith("]"):
                    return row[i : j + 1]
            return []
    return []


def guide_drugs(rows):
    """복약안내 표: 약품마다 [분류] 글자가 있는 행에서 시작하는 카드로 읽는다."""
    header = next((row for row in rows if any(compact(b.text) == "주의사항" for b in row)), None)
    if not header:
        return []
    warning_x = next(b for b in header if compact(b.text) == "주의사항").x0 - 30
    bottom = next((r for r, row in enumerate(rows) if row and compact(row[0].text) == "1일"), len(rows))

    starts = [r for r, row in enumerate(rows[:bottom]) if category_boxes(row)]
    if not starts:
        return []
    ends = [*starts[1:], bottom]
    return [read_guide_card(rows, start, end, warning_x) for start, end in zip(starts, ends, strict=True)]


def read_guide_card(rows, start, end, warning_x):
    """복약안내 표에서 약 하나의 카드(start 행부터 end 행 전까지)를 읽는다."""
    first = rows[start]
    category_parts = category_boxes(first)
    category = category_parts[0]
    category_end = category_parts[-1].x1
    dose_boxes = [b for b in first if b.x0 > category_end and b.cx < warning_x]
    dose_x = dose_boxes[0].x0 - 10 if dose_boxes else warning_x

    name, looks, effect, storage, warning = [], [], [], [], []
    for r in range(start, end):
        for b in rows[r]:
            if b.cx >= warning_x:
                if len(b.text) > 1:  # 아이콘이 'p' 같은 글자로 읽힌 것은 버린다.
                    warning.append(b.text)
            elif b.x0 >= dose_x:
                if r > start:
                    storage.append(b.text)
            elif b.x0 >= category.x0 - 10:
                if b not in category_parts:
                    effect.append(b.text)
            else:
                (name if r == start else looks).append(b.text)

    return {
        "명칭": " ".join(name) or None,
        "성상": " ".join(looks) or None,
        "분류": " ".join(b.text for b in category_parts).strip("[]"),
        "효능": " ".join(effect) or None,
        "복용법": " ".join(b.text for b in dose_boxes) or None,
        **parse_dose(" ".join(b.text for b in dose_boxes)),
        "보관": " ".join(storage) or None,
        "주의사항": " ".join(warning) or None,
        "신뢰도": average_confidence([b for r in range(start, end) for b in rows[r]]),
    }


def taking_box(rows):
    """맨 아래 '1일 ( )회 ( )일분  □식전 30분 □식후 30분' 손글씨 칸.

    손글씨 숫자는 '3' '0일분'처럼 쪼개져 읽히기도 해서 공백을 없앤 글자로 찾는다.
    체크 표시는 OCR이 '☑식후'처럼 읽어낸 경우에만 알 수 있다.
    """
    for row in rows:
        if not row or compact(row[0].text) != "1일":
            continue
        text = compact(row_text(row))
        times = re.search(r"1일(\d+)회", text)
        days = re.search(r"회(\d+)일분", text)
        checked = re.search(r"[☑✓✔](식전|식후)(\d+)분", text)
        return {
            "1일횟수": int(times.group(1)) if times else None,
            "일분": int(days.group(1)) if days else None,
            "복용시점": f"{checked.group(1)} {checked.group(2)}분" if checked else None,
        }
    return {"1일횟수": None, "일분": None, "복용시점": None}


def guide(rows):
    patient = after_colon(rows, "환자정보") or ""
    age = AGE.search(patient)
    next_visit = after_colon(rows, "(다음내방일")
    return {
        "환자": {
            "성명": re.sub(r"\(.*", "", patient).strip() or None,
            "나이": int(age.group(1)) if age else None,
        },
        "교부번호": pattern(after_colon(rows, "교부번호"), re.compile(r"\d+")),
        "병원": after_colon(rows, "병원정보"),
        "조제약사": after_colon(rows, "조제약사"),
        "조제일자": pattern(after_colon(rows, "조제일자"), DATE),
        "다음내방일": pattern(next_visit, DATE),
    }


def parse(fields):
    if not fields:
        return None
    left, right = split_panels(to_boxes(fields))
    left_rows, right_rows = build_rows(left), build_rows(right)
    return {
        "복약안내": guide(right_rows),
        "약품": guide_drugs(right_rows),
        "복용표시": taking_box(right_rows),
        "영수증": receipt(left_rows),
    }
