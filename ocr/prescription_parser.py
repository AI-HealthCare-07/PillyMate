"""CLOVA OCR 결과를 처방전 항목별 dict(한글 키)로 정리한다.

좌표 처리는 text_layout_utils를 쓰고, 이 파일은 처방전 양식의 라벨·표 위치만 안다.
결과의 한글 키는 ocr_result_formatter가 API 명세 형식(snake_case)으로 바꾼다.
환자 성명·주민등록번호도 여기서는 읽어 두지만, 마스킹에만 쓰이고 모듈 밖으로 나가지 않는다.
"""

import math
import re
from statistics import median

from ocr.text_layout_utils import average_confidence, build_rows, compact, to_boxes, to_number

PHONE = re.compile(r"\d{2,4}-\d{3,4}-\d{4}")
RESIDENT_NO = re.compile(r"\d{6}-[\d*]{7}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
KOREAN_DATE = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")
DASH_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
ISSUE_NO = re.compile(r"제\s*(\d+)")
DRUG = re.compile(r"^(\d{9})\s*(.*)$")
NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
NAME = re.compile(r"^[가-힣]{2,5}$")
CHECK_MARKS = {"V", "v", "√", "✓", "✔"}


# OCR이 라벨 글자를 비슷한 글자로 잘못 읽는 경우(칭 → 청)를 함께 찾는다.
LABEL_VARIANTS = {"명칭": ("명칭", "명청")}


def find_label(rows, label):
    """띄어 쓴 라벨(예: '명  칭')도 찾을 수 있도록 행의 글자를 공백 없이 이어 비교한다.
    가장 위쪽에서 찾은 (행 번호, 라벨이 끝나는 상자 번호)를 돌려준다."""
    for r, row in enumerate(rows):
        joined, owner = "", []
        for i, box in enumerate(row):
            piece = compact(box.text)
            joined += piece
            owner += [i] * len(piece)
        for variant in LABEL_VARIANTS.get(label, (label,)):
            at = joined.find(variant)
            if at >= 0:
                return r, owner[at + len(variant) - 1]
    return None


def text_after(rows, label):
    found = find_label(rows, label)
    if not found:
        return None
    r, i = found
    return " ".join(box.text for box in rows[r][i + 1 :]) or None


def cell_after(rows, label):
    """라벨 오른쪽 첫 번째 칸의 글자(가까이 붙은 상자들)를 돌려준다."""
    found = find_label(rows, label)
    if not found:
        return None
    r, i = found
    rest = rows[r][i + 1 :]
    if not rest:
        return None
    cell = [rest[0]]
    for box in rest[1:]:
        if box.x0 - cell[-1].x1 > 1.5 * box.h:
            break
        cell.append(box)
    return " ".join(box.text for box in cell)


def search_after(rows, label, pattern):
    text = text_after(rows, label)
    found = pattern.search(text) if text else None
    return found.group() if found else None


def all_boxes(rows):
    return [box for row in rows for box in row]


def first_box(rows, text):
    return next((b for b in all_boxes(rows) if compact(b.text) == text), None)


def insurance(rows):
    """번호 대신 V 표시가 들어간 칸 오른쪽 글자가 선택된 보험 종류다."""
    for row in rows:
        for box, following in zip(row, row[1:], strict=False):
            if box.text in CHECK_MARKS:
                return re.sub(r"[\s(]+$", "", following.text)
    return None


def issue_date(rows):
    text = "\n".join(" ".join(b.text for b in row) for row in rows)
    found = KOREAN_DATE.search(text) or DASH_DATE.search(text_after(rows, "교부일자") or "")
    if not found:
        return None
    year, month, day = found.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def disease_code_area(rows):
    """질병분류기호 칸의 (x_min, x_max, y_min, y_max).

    '질병'/'기호' 라벨은 OCR이 다른 글자로 읽기도 해서(질병 → 볼륨) 위아래 줄을 먼저 쓴다.
    위: '주민등록번호' 줄 아래 / 아래: '*환자의 요구가 …' 안내문 위 / 오른쪽: '의료인의' 칸 왼쪽.
    """
    boxes = all_boxes(rows)
    resident = first_box(rows, "주민등록번호")
    notice = next((b for b in boxes if "환자의" in b.text), None)
    doctor = first_box(rows, "의료인의")
    labels = [b for b in boxes if compact(b.text) in ("질병", "분류", "기호")]

    if resident and notice and resident.y1 < notice.y0:
        y_min, y_max = resident.y1, notice.y0
    elif labels:
        y_min = min(b.y0 for b in labels) - max(b.h for b in labels)
        y_max = max(b.y1 for b in labels) + max(b.h for b in labels)
    else:
        return None
    # 왼쪽 라벨 칸 글자는 한글이라 글자 종류 검사에서 걸러지지만, 찾았으면 그 오른쪽만 본다.
    x_min = max((b.x1 for b in labels), default=-math.inf)
    x_max = doctor.x0 if doctor else math.inf
    return x_min, x_max, y_min, y_max


def disease_codes(rows):
    """질병분류기호 칸 안의 한 글자 칸들을 행별로 잇는다."""
    area = disease_code_area(rows)
    if not area:
        return []
    x_min, x_max, y_min, y_max = area

    # 작은 칸 글자는 대문자를 소문자로 읽는 경우가 많다(S → s). 대소문자 모두 받는다.
    chars = sorted(
        (
            b
            for b in all_boxes(rows)
            if x_min < b.cx < x_max and y_min < b.cy < y_max and re.fullmatch(r"[A-Za-z0-9.]+", b.text)
        ),
        key=lambda b: b.cy,
    )
    if not chars:
        return []
    # 소문자 상자는 숫자보다 낮고 작아서 build_rows의 기준으로는 다른 행으로 갈라질 수 있다.
    # 글자 높이를 기준으로 세로 위치가 가까운 칸끼리 한 행으로 묶는다.
    tolerance = 0.5 * median(b.h for b in chars)
    lines = []
    for box in chars:
        if lines and box.cy - lines[-1][-1].cy < tolerance:
            lines[-1].append(box)
        else:
            lines.append([box])

    codes = []
    for line in lines:
        code = "".join(b.text for b in sorted(line, key=lambda b: b.x0)).replace(".", "")
        code = normalize_disease_code(code)
        if code:
            codes.append(code)
    return codes


# 코드 뒷부분은 숫자만 오므로 숫자와 비슷하게 생긴 글자를 숫자로 고친다.
DIGIT_LOOKALIKES = str.maketrans(
    {"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "i": "1", "Z": "2", "z": "2", "B": "8"}
)


def normalize_disease_code(text):
    """'s800' → 'S800'. 첫 글자는 영문 대문자, 나머지는 숫자로 맞춘다."""
    if len(text) < 3 or not text[0].isalpha():
        return None
    code = text[0].upper() + text[1:].translate(DIGIT_LOOKALIKES)
    return code if re.fullmatch(r"[A-Z]\d{2,4}", code) else None


def doctor_name(rows):
    """'처방 의료인의 성명' 라벨 바로 오른쪽에 있는 이름(도장 글자보다 왼쪽)."""
    label = first_box(rows, "의료인의")
    if not label:
        return None
    candidates = [
        b for b in all_boxes(rows) if b.x0 > label.x1 and abs(b.cy - label.cy) < 2 * label.h and NAME.match(b.text)
    ]
    return min(candidates, key=lambda b: b.x0).text if candidates else None


def drugs(rows):
    columns = {key: first_box(rows, key) for key in ("투약량", "투여횟수", "투약일수", "구분기호")}
    if not all(columns[key] for key in ("투약량", "투여횟수", "투약일수")):
        return []
    usage_from = (columns["구분기호"] or columns["투약일수"]).x1
    numeric = {"1회투약량": columns["투약량"], "1일투여횟수": columns["투여횟수"], "총투약일수": columns["투약일수"]}
    name_until = columns["투약량"].x0
    half_width = 0.5 * (columns["투여횟수"].cx - columns["투약량"].cx)

    items = []
    for row in rows:
        for i, box in enumerate(row):
            match = DRUG.match(box.text)
            if not match:
                continue
            rest = row[i + 1 :]
            name = " ".join([match.group(2)] + [b.text for b in rest if b.x1 <= name_until])
            name = re.sub(r"^[^\w가-힣]+", "", name.strip())  # 앞에 붙은 ':' 같은 잡글자 제거
            item = {"코드": match.group(1), "명칭": name}
            for key, header in numeric.items():
                value = next(
                    (b.text for b in rest if NUMBER.match(b.text) and abs(b.cx - header.cx) < half_width),
                    None,
                )
                item[key] = to_number(value) if value else None
            item["용법"] = " ".join(b.text for b in rest if b.x0 >= usage_from) or None
            item["신뢰도"] = average_confidence([box, *rest])
            items.append(item)
            break
    return items


def parse(fields):
    if not fields:
        return None
    rows = build_rows(to_boxes(fields))
    text = "\n".join(" ".join(b.text for b in row) for row in rows)
    issue_no = ISSUE_NO.search(text_after(rows, "교부번호") or "")
    # OCR이 '제'를 놓치는 경우가 있어 숫자만으로도 찾는다.
    license_no = re.search(r"(?:제\s*)?(\d{3,})", text_after(rows, "면허번호") or "")
    period = re.search(r"교부일부터\s*\(\s*(\d+)\s*\)", text)
    agency = re.search(r"요양기관기호\s*:?\s*(\d+)", text)
    email = EMAIL.search(text)

    return {
        "보험종류": insurance(rows),
        "요양기관기호": agency.group(1) if agency else None,
        "교부일": issue_date(rows),
        "교부번호": issue_no.group(1) if issue_no else None,
        "환자": {
            "성명": cell_after(rows, "성명"),
            "주민등록번호": search_after(rows, "주민등록번호", RESIDENT_NO),
        },
        "의료기관": {
            "명칭": cell_after(rows, "명칭"),
            "전화번호": search_after(rows, "전화번호", PHONE),
            "팩스번호": search_after(rows, "팩스번호", PHONE),
            "이메일": email.group() if email else None,
        },
        "질병분류기호": disease_codes(rows),
        "처방의료인": {
            "성명": doctor_name(rows),
            "면허종별": cell_after(rows, "면허종별"),
            "면허번호": license_no.group(1) if license_no else None,
        },
        "처방의약품": drugs(rows),
        "사용기간_일": int(period.group(1)) if period else None,
    }
