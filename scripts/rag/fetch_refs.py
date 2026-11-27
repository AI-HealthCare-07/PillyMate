"""4단계(선택): 공공데이터포털 e약은요 API로 drug_refs.json의 빈칸을 미리 채운다.

주의
- e약은요는 **일반의약품만** 있다. 소아과 처방약 대부분(항생제 시럽 등 전문의약품)은 안 나온다.
  → 그런 약은 의약품안전나라(nedrug.mfds.go.kr)에서 직접 찾아 채운다.
- 채운 항목은 status를 "review"로 둔다. 사람이 읽고 2~3문장으로 줄인 뒤 "done"으로 바꿔야 가이드에 쓰인다.
- API 키는 환경변수 DATA_GO_KR_KEY (디코딩된 키). 저장소에 올리지 않는다 (NFR-SEC-002).
- 엔드포인트·필드명은 data.go.kr '의약품개요정보(e약은요)' 상세 페이지에서 한 번 확인할 것.

    export DATA_GO_KR_KEY=...
    uv run python scripts/rag/fetch_refs.py            # 비어 있는 todo 항목만
    uv run python scripts/rag/fetch_refs.py --dry-run  # 저장하지 않고 결과만 보기
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "app" / "data" / "drug_refs.json"
ENDPOINT = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"


def clean(s: str | None) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def search(key: str, item_name: str) -> list[dict]:
    q = urllib.parse.urlencode({"serviceKey": key, "itemName": item_name, "type": "json", "numOfRows": 5})
    with urllib.request.urlopen(f"{ENDPOINT}?{q}", timeout=15) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body.get("body", {}).get("items") or []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        sys.exit("환경변수 DATA_GO_KR_KEY가 없어요.")

    data = json.loads(REFS.read_text(encoding="utf-8"))
    hit = miss = 0
    for d in data["drugs"]:
        if d["status"] != "todo":
            continue
        items = []
        for q in [d["names"][0], d["key"]]:
            try:
                items = search(key, q)
            except Exception as e:  # 네트워크·키 오류는 건너뛰고 계속
                print(f"  [오류] {q}: {e}")
            if items:
                break
            time.sleep(0.2)
        if not items:
            miss += 1
            print(f"  없음  {d['names'][0]}  (전문의약품일 가능성 → 의약품안전나라에서 직접)")
            continue
        it = items[0]
        hit += 1
        d.update(
            {
                "item_seq": it.get("itemSeq", ""),
                "efficacy": clean(it.get("efcyQesitm")),
                "cautions": clean(
                    " ".join(filter(None, [it.get("atpnWarnQesitm"), it.get("atpnQesitm"), it.get("intrcQesitm")]))
                ),
                "side_effects": clean(it.get("seQesitm")),
                "storage": clean(it.get("depositMethodQesitm")),
                "source": {
                    "name": "식약처 의약품개요정보(e약은요)",
                    "url": "https://nedrug.mfds.go.kr",
                    "checked_at": date.today().isoformat(),
                },
                "status": "review",  # 사람이 읽고 줄인 뒤 done으로
            }
        )
        # useMethodQesitm(용법·용량)은 일부러 가져오지 않는다 (NFR-SAFE-002)
        print(f"  찾음  {d['names'][0]} → {it.get('itemName')}")

    print(f"\n찾음 {hit}개, 못 찾음 {miss}개")
    if not args.dry_run:
        REFS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"저장: {REFS.relative_to(ROOT)}  (status=review 항목을 읽고 다듬은 뒤 done으로 바꾸세요)")


if __name__ == "__main__":
    main()
