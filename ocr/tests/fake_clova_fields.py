"""테스트용 가짜 CLOVA OCR 응답(fields)을 실제 양식처럼 좌표를 배치해 만든다.

실제 사진 없이도 파서가 라벨·표 위치로 값을 찾는지 확인할 수 있다.
가상 처방전이며 이름·번호는 모두 지어낸 값이다.
"""

import math

TEXT_HEIGHT = 16


def text_width(text, height=TEXT_HEIGHT):
    return len(text) * height * 0.8


def fake_field(text, x, y, *, width=None, height=TEXT_HEIGHT, confidence=0.95, line_break=False):
    """왼쪽 위 (x, y)에 놓인 글자 상자 하나."""
    width = text_width(text, height) if width is None else width
    return {
        "inferText": text,
        "inferConfidence": confidence,
        "lineBreak": line_break,
        "boundingPoly": {
            "vertices": [
                {"x": x, "y": y},
                {"x": x + width, "y": y},
                {"x": x + width, "y": y + height},
                {"x": x, "y": y + height},
            ]
        },
    }


def centered_field(text, center_x, y, **kwargs):
    """가운데가 center_x에 오도록 놓인 글자 상자 (표의 숫자 칸)."""
    return fake_field(text, center_x - text_width(text) / 2, y, **kwargs)


def center_of(text, x):
    return x + text_width(text) / 2


def rotate_fields(fields, angle):
    """사진이 angle(라디안)만큼 기울어진 것처럼 모든 좌표를 돌린다."""
    cos, sin = math.cos(angle), math.sin(angle)
    rotated = []
    for field in fields:
        vertices = [
            {"x": v["x"] * cos - v["y"] * sin, "y": v["x"] * sin + v["y"] * cos}
            for v in field["boundingPoly"]["vertices"]
        ]
        rotated.append({**field, "boundingPoly": {"vertices": vertices}})
    return rotated


def fake_prescription_fields():
    """처방전 한 장: 보험 종류, 교부번호, 의료기관·환자, 질병분류기호, 의료인, 약 2개."""
    header_x = {"투약량": 500, "투여횟수": 580, "투약일수": 670, "구분기호": 760, "용법": 850}
    header_cx = {key: center_of(key, x) for key, x in header_x.items()}

    def drug_row(y, code, name, dose, per_day, days, usage_words):
        row = [
            fake_field(code, 40, y),
            fake_field(name, 140, y, width=340),
            centered_field(dose, header_cx["투약량"], y),
            centered_field(per_day, header_cx["투여횟수"], y),
            centered_field(days, header_cx["투약일수"], y),
        ]
        x = 860
        for word in usage_words:
            row.append(fake_field(word, x, y))
            x += text_width(word) + 8
        return row

    return [
        fake_field("V", 40, 50),
        fake_field("건강보험", 70, 50),
        fake_field("2", 170, 50),
        fake_field("의료급여", 200, 50),
        fake_field("요양기관기호", 40, 90),
        fake_field(":", 150, 90),
        fake_field("31283746", 170, 90),
        fake_field("교부번호", 40, 130),
        *[
            fake_field(text, x, 130)
            for text, x in [("2026", 160), ("년", 230), ("11", 260), ("월", 295), ("12", 320), ("일", 355)]
        ],
        fake_field("-", 380, 130),
        fake_field("제", 400, 130),
        fake_field("00231", 425, 130),
        fake_field("호", 500, 130),
        fake_field("명", 40, 170),
        fake_field("칭", 70, 170),
        fake_field("해솔소아청소년과의원", 160, 170),
        fake_field("성", 600, 170),
        fake_field("명", 630, 170),
        fake_field("김하윤", 700, 170),
        fake_field("전화번호", 40, 210),
        fake_field("031-764-2210", 160, 210),
        fake_field("주민등록번호", 600, 210),
        fake_field("230512-4083217", 760, 210),
        fake_field("팩스번호", 40, 250),
        fake_field("031-764-2211", 160, 250),
        fake_field("e-mail", 600, 250),
        fake_field("haesol.ped@example.com", 700, 250),
        fake_field("질병", 40, 300),
        *[fake_field(text, x, 300) for text, x in [("J", 120), ("0", 145), ("0", 170)]],
        fake_field("처방", 400, 300),
        fake_field("의료인의", 460, 300),
        fake_field("성", 560, 300),
        fake_field("명", 585, 300),
        fake_field("박정민", 640, 300),
        fake_field("분류", 40, 330),
        *[fake_field(text, x, 330) for text, x in [("J", 120), ("2", 145), ("0", 170), ("9", 195)]],
        fake_field("기호", 40, 355),
        fake_field("*환자의", 40, 385),
        fake_field("요구가", 130, 385),
        fake_field("면허종별", 40, 420),
        fake_field("의사", 160, 420),
        fake_field("면허번호", 400, 420),
        fake_field("제", 500, 420),
        fake_field("84213", 530, 420),
        fake_field("호", 610, 420),
        *[fake_field(text, x, 470) for text, x in header_x.items()],
        *drug_row(510, "643901230", "세파클러건조시럽(내복)/60(1)mL/병", "4.2", "3", "5", ["->식후", "30분"]),
        *drug_row(
            550,
            "652600871",
            "세토펜현탁액(아세트아미노펜)/100(1)mL/병",
            "5",
            "4",
            "3",
            ["필요시", "1일", "최대", "4회"],
        ),
        fake_field("교부일부터", 40, 610),
        fake_field("(", 130, 610),
        fake_field("3", 145, 610),
        fake_field(")", 160, 610),
        fake_field("일간", 175, 610),
    ]


def fake_medicine_bag_fields():
    """약봉투 한 장: 왼쪽 영수증(약 2개 표) + 오른쪽 복약안내(약 3개 카드) + 복용 표시 칸."""
    receipt_x = {"약품명": 40, "투약량": 260, "횟수": 340, "일수": 420, "총투": 500}
    receipt_cx = {key: center_of(key, x) for key, x in receipt_x.items()}

    def receipt_row(y, name, *numbers):
        row = [fake_field(name, 40, y, width=180)]
        for key, value in zip(("투약량", "횟수", "일수", "총투"), numbers, strict=True):
            row.append(centered_field(value, receipt_cx[key], y))
        return row

    left_panel = [
        *[
            fake_field(t, x, 40)
            for t, x in [("영수증번호", 40), ("2026-1112-0042", 160), ("투약일수", 330), ("5", 420)]
        ],
        fake_field("환자성명", 40, 80),
        fake_field("김하윤", 160, 80),
        fake_field("조제일자", 40, 120),
        fake_field("2026-11-12", 160, 120),
        fake_field("약제비총액", 40, 160),
        fake_field("15,300원", 160, 160),
        fake_field("본인부담금", 40, 200),
        fake_field("4,600원", 160, 200),
        fake_field("보험자부담금", 40, 240),
        fake_field("10,700원", 160, 240),
        fake_field("비급여(전액본인)", 40, 280),
        fake_field("0원", 200, 280),
        fake_field("합계", 40, 320),
        fake_field("4,600원", 160, 320),
        fake_field("사업자등록번호", 40, 360),
        fake_field("123-45-67890", 160, 360),
        fake_field("상호", 40, 440),
        fake_field("해솔약국", 160, 440),
        fake_field("성명", 40, 480),
        fake_field("이수진", 160, 480),
        fake_field("발행일", 40, 520),
        fake_field("2026-11-12", 160, 520),
        *[fake_field(text, x, 570) for text, x in receipt_x.items()],
        *receipt_row(610, "세파클러건조시럽", "4.2", "3", "5", "63"),
        *receipt_row(650, "비오플250산", "1", "2", "5", "10"),
    ]

    right_panel = [
        fake_field("환자정보", 650, 40),
        fake_field(":", 740, 40),
        fake_field("김하윤(만", 760, 40),
        fake_field("3세)", 860, 40),
        fake_field("교부번호", 1000, 40),
        fake_field(":", 1090, 40),
        fake_field("00231", 1110, 40),
        fake_field("병원정보", 650, 80),
        fake_field(":", 740, 80),
        fake_field("해솔소아청소년과의원", 760, 80),
        fake_field("조제약사", 650, 120),
        fake_field(":", 740, 120),
        fake_field("이수진", 760, 120),
        fake_field("조제일자", 1000, 120),
        fake_field(":", 1090, 120),
        fake_field("2026-11-12", 1110, 120),
        fake_field("(다음내방일", 650, 160),
        fake_field(":", 770, 160),
        fake_field("2026-11-19)", 790, 160),
        *[
            fake_field(text, x, 210)
            for text, x in [("약품사진", 650), ("약품명", 760), ("효능", 900), ("복용법", 1040), ("주의사항", 1250)]
        ],
        # 약 1: 먹는 항생제
        fake_field("세파클러건조시럽", 760, 250, width=120),
        fake_field("[항생제]", 900, 250),
        fake_field("4.2mL씩", 1040, 250),
        fake_field("3회", 1135, 250),
        fake_field("5일분", 1165, 250),
        fake_field("설사시", 1250, 250),
        fake_field("분홍색", 760, 280),
        fake_field("현탁액", 820, 280),
        fake_field("세균", 900, 280),
        fake_field("감염", 940, 280),
        fake_field("냉장", 1040, 280),
        fake_field("보관", 1080, 280),
        # 약 2: 필요할 때 먹는 해열제
        fake_field("세토펜현탁액", 760, 330, width=120),
        fake_field("[해열진통제]", 900, 330),
        fake_field("5mL씩", 1040, 330),
        fake_field("필요시", 1110, 330),
        fake_field("1일", 1250, 330),
        fake_field("최대", 1285, 330),
        fake_field("4회", 1325, 330),
        fake_field("흰색", 760, 360),
        fake_field("현탁액", 800, 360),
        # 약 3: 바르는 연고
        fake_field("후시딘연고", 760, 410, width=120),
        fake_field("[외용", 900, 410),
        fake_field("항생제]", 950, 410),
        fake_field("적당량", 1040, 410),
        fake_field("2회", 1095, 410),
        fake_field("7일분", 1130, 410),
        fake_field("흰색", 760, 440),
        fake_field("연고", 800, 440),
        # 맨 아래 복용 표시 칸
        *[
            fake_field(t, x, 490)
            for t, x in [("1일", 650), ("3회", 700), ("5일분", 750), ("☑식후", 830), ("30분", 900)]
        ],
    ]
    return left_panel + right_panel
