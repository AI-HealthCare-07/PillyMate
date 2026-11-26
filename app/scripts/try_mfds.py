"""식약처 「의약품 제품 허가정보」 API가 내 인증키로 응답하는지 확인하는 개발용 스크립트.

실행 (저장소 루트에서):
    uv run --env-file .env python -m app.scripts.try_mfds 기능이름 약이름
    uv run --env-file .env python -m app.scripts.try_mfds 기능이름 --edi 643901230

- 기능이름: 공공데이터포털 API 페이지 아래 '활용명세'에 나오는 영문 이름 (예: getDrugPrdtPrmsnInq07)
- 주소는 app/core/config.py 의 MFDS_PERMIT_URL, 인증키는 .env 의 MFDS_API_KEY (Decoding 키) 를 써요.
  인증키는 화면에 출력하지 않아요.
- 결과에서 제품명·보험코드·주성분만 골라 보여 줘요.
"""

import argparse
import json
import sys

import httpx

from app.core import config

SHOW_KEYS = ("ITEM_NAME", "EDI_CODE", "ITEM_INGR_NAME", "MAIN_ITEM_INGR", "ENTP_NAME", "ITEM_SEQ")


def main() -> None:
    parser = argparse.ArgumentParser(description="식약처 의약품 제품 허가정보 API 시험 호출")
    parser.add_argument("operation", help="활용명세의 기능 이름 (예: getDrugPrdtPrmsnInq07)")
    parser.add_argument("item_name", nargs="?", help="찾을 약 이름 (예: 세토펜)")
    parser.add_argument("--edi", help="보험코드 9자리로 찾기")
    args = parser.parse_args()

    key = config.MFDS_API_KEY
    if not key:
        sys.exit(".env 에 MFDS_API_KEY 가 없어요. --env-file .env 를 붙였는지도 확인해 주세요.")
    if not args.item_name and not args.edi:
        sys.exit("약 이름이나 --edi 보험코드 중 하나를 넣어 주세요.")

    params = {"serviceKey": key, "type": "json", "pageNo": 1, "numOfRows": 5}
    if args.item_name:
        params["item_name"] = args.item_name
    if args.edi:
        params["edi_code"] = args.edi

    url = f"{config.MFDS_PERMIT_URL}/{args.operation}"
    try:
        res = httpx.get(url, params=params, timeout=15)
    except httpx.HTTPError as e:
        sys.exit(f"연결 실패: {e}")

    print(f"HTTP {res.status_code}")
    try:
        data = res.json()
    except json.JSONDecodeError:
        # 키 오류 등은 XML로 올 때가 많아요. 키가 섞여 나오지 않게 앞부분만 보여 줘요.
        print(res.text[:500].replace(key, "***"))
        return

    header = (data.get("header") or {}) if isinstance(data, dict) else {}
    print("결과코드:", header.get("resultCode"), header.get("resultMsg"))
    body = data.get("body") or {}
    items = body.get("items") or []
    if isinstance(items, dict):  # 결과가 1건이면 dict로 올 때가 있어요
        items = items.get("item") or []
        items = items if isinstance(items, list) else [items]
    print("전체 건수:", body.get("totalCount"))
    for i, it in enumerate(items, 1):
        print(f"\n[{i}]")
        for k in SHOW_KEYS:
            if k in it:
                print(f"  {k}: {it[k]}")
        if i == 1:
            print("  (응답에 있는 항목 이름:", ", ".join(it.keys()), ")")


if __name__ == "__main__":
    main()
