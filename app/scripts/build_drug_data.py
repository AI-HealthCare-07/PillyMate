"""식약처 「의약품 제품 허가정보」 API → app/data/drug_permit.csv (약효 조회 drug_lookup.py가 읽는 파일).

실행 (저장소 루트에서, try_mfds와 같은 .env의 MFDS_API_KEY·MFDS_PERMIT_URL을 쓴다):
    uv run --env-file .env python -m app.scripts.build_drug_data 기능이름
    uv run --env-file .env python -m app.scripts.build_drug_data 기능이름 --limit 300   # 시험용으로 조금만

- 기능이름: getDrugPrdtPrmsnDtlInq08 (허가 상세정보). ATC 코드·성상·보험코드가 함께 나온다.
  서비스 버전(08)이 바뀌면 try_mfds로 '응답에 있는 항목 이름'을 보고 다시 정한다.
- 허가가 취소·취하된 품목(CANCEL_DATE가 있는 것)은 저장하지 않는다.
- 긴 문서 항목(효능효과·용법용량 원문 등)은 버리고 FIELDS에 적은 짧은 항목만 저장한다.
- 전체를 받으면 수만 건이라 시간이 걸린다. 한 페이지 100건씩, 실패하면 잠시 쉬고 다시 시도한다.
- 인증키는 화면·파일에 남기지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.core import config
from app.services.drug_lookup import DRUG_DATA_PATH

# 저장할 항목. 응답에 없는 항목은 빈 칸으로 남는다. drug_lookup.COLUMN_MAP과 이름을 맞춘다.
FIELDS = (
    "ITEM_SEQ",
    "ITEM_NAME",
    "ITEM_INGR_NAME",
    "MAIN_ITEM_INGR",
    "EDI_CODE",
    "CLASS_NO",
    "CLASS_NAME",
    "CHART",
    "ATC_CODE",
    "ETC_OTC_CODE",
    "CANCEL_DATE",
)
PAGE_SIZE = 100
RETRIES = 3


def items_of(data: Any) -> tuple[list[dict], int | None]:
    """응답 JSON → (항목 목록, 전체 건수). 결과가 1건이면 dict로 오는 경우도 받는다."""
    body = (data.get("body") or {}) if isinstance(data, dict) else {}
    items = body.get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
        items = items if isinstance(items, list) else [items]
    total = body.get("totalCount")
    return [i for i in items if isinstance(i, dict)], int(total) if total is not None else None


def fetch_page(client: httpx.Client, url: str, key: str, page: int) -> tuple[list[dict], int | None]:
    params = {"serviceKey": key, "type": "json", "pageNo": page, "numOfRows": PAGE_SIZE}
    last_error = ""
    for attempt in range(1, RETRIES + 1):
        try:
            res = client.get(url, params=params, timeout=30)
            return items_of(res.json())
        except (httpx.HTTPError, ValueError) as e:  # ValueError: JSON이 아닌 응답(키 오류 XML 등)
            last_error = str(e).replace(key, "***")
            time.sleep(2 * attempt)
    raise RuntimeError(f"{page}쪽을 {RETRIES}번 시도했지만 받지 못했어요: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="식약처 허가정보 → 약효 조회용 CSV")
    parser.add_argument("operation", help="활용명세의 기능 이름")
    parser.add_argument("--limit", type=int, help="이만큼만 받기 (시험용)")
    parser.add_argument("--out", type=Path, default=DRUG_DATA_PATH, help=f"저장 위치 (기본 {DRUG_DATA_PATH})")
    args = parser.parse_args()

    key = config.MFDS_API_KEY
    if not key:
        sys.exit(".env 에 MFDS_API_KEY 가 없어요. --env-file .env 를 붙였는지도 확인해 주세요.")
    url = f"{config.MFDS_PERMIT_URL}/{args.operation}"

    rows: list[dict] = []
    seen_keys: set[str] = set()
    page, total = 1, None
    with httpx.Client() as client:
        while True:
            items, page_total = fetch_page(client, url, key, page)
            total = total or page_total
            if page == 1 and items:
                seen_keys = set(items[0])
                missing = [f for f in FIELDS if f not in seen_keys]
                print("응답 항목:", ", ".join(sorted(seen_keys)))
                if missing:
                    print("응답에 없어 빈 칸이 될 항목:", ", ".join(missing))
            if not items:
                break
            rows.extend(
                {f: " ".join(str(i.get(f) or "").split()) for f in FIELDS} for i in items
            )  # 줄바꿈·겹친 공백 정리
            print(f"\r{len(rows)} / {total or '?'}", end="", flush=True)
            if args.limit and len(rows) >= args.limit:
                rows = rows[: args.limit]
                break
            if total is not None and len(rows) >= total:
                break
            page += 1
            time.sleep(0.1)  # 공공 API에 부담을 덜 주게

    print()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        kept = [r for r in rows if r["ITEM_NAME"] and not r["CANCEL_DATE"]]
        writer.writerows(kept)
    print(f"{len(rows)}건 중 허가가 살아 있는 {len(kept)}건을 {args.out}에 저장했어요.")
    if not {"ATC_CODE", "CLASS_NO", "CLASS_NAME"} & seen_keys:
        print("주의: 분류 항목(ATC_CODE·CLASS_NO)이 없어요. 허가 상세정보 기능을 썼는지 확인해 주세요.")


if __name__ == "__main__":
    main()
