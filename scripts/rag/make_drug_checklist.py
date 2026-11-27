"""2단계: 가상 데이터에서 '찾아야 할 약' 체크리스트와 drug_refs.json 빈 틀을 만든다.

실행 (저장소 루트에서):
    uv run python scripts/rag/make_drug_checklist.py \
        --medication data/sample/medication.csv \
        --provenance data/sample/provenance_medication.csv

결과:
    app/data/drug_checklist.csv   ← 사람이 보면서 하나씩 찾는 목록 (처방 많은 순)
    app/data/drug_refs.json       ← 빈칸을 채울 틀. 이미 채운 항목은 덮어쓰지 않음

컬럼 이름이 다르면 --name-col, --ingredient-col 로 지정한다.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.services.guide.drug_name_normalize import bracket_text, normalize_name  # noqa: E402

DATA_DIR = ROOT / "app" / "data"
NAME_CANDIDATES = ["name", "drug_name", "product_name", "약품명", "제품명"]
INGR_CANDIDATES = ["ingredient", "ingredient_name", "성분", "성분명", "main_ingredient"]
FORM_CANDIDATES = ["dosage_form", "제형"]
NEDRUG_SEARCH = "https://nedrug.mfds.go.kr/searchDrug?itemName="


def read_csv(path: Path) -> list[dict]:
    # 엑셀에서 저장한 CSV(BOM)도 읽히도록 utf-8-sig
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pick(cols: list[str], wanted: str | None, candidates: list[str]) -> str | None:
    if wanted:
        if wanted not in cols:
            sys.exit(f"컬럼 '{wanted}'이 없어요. 있는 컬럼: {cols}")
        return wanted
    return next((c for c in candidates if c in cols), None)


def empty_entry(key: str, name: str, ingredient: str, forms: list[str]) -> dict:
    return {
        "key": key,
        "names": [name],  # 처방전에 찍히는 다른 이름(별칭)은 여기에 추가
        "ingredient": ingredient,  # 성분 (한글 또는 영문)
        "dosage_forms": forms,
        "item_seq": "",  # 식약처 품목기준코드 (의약품안전나라 상세 화면)
        "efficacy": "",  # 무슨 약인지 (효능효과) — 1~2문장
        "cautions": "",  # 주의사항 — 소아·알레르기 관련 위주, 2~3문장
        "side_effects": "",  # 흔한 부작용
        "storage": "",  # 보관법
        "source": {"name": "", "url": "", "checked_at": ""},
        "status": "todo",  # 다 채우면 "done" — done만 가이드에 쓰임
    }
    # 용법·용량은 일부러 칸이 없다. 성인 용량이 LLM에 들어가는 것을 막기 위함 (NFR-SAFE-002)


def main() -> None:  # noqa: C901
    ap = argparse.ArgumentParser()
    ap.add_argument("--medication", required=True, type=Path)
    ap.add_argument("--provenance", type=Path, help="성분이 medication.csv에 없을 때")
    ap.add_argument("--name-col")
    ap.add_argument("--ingredient-col")
    args = ap.parse_args()

    meds = read_csv(args.medication)
    if not meds:
        sys.exit("medication.csv가 비어 있어요.")
    cols = list(meds[0].keys())
    name_col = pick(cols, args.name_col, NAME_CANDIDATES)
    if not name_col:
        sys.exit(f"약 이름 컬럼을 못 찾았어요. --name-col 로 지정해 주세요. 있는 컬럼: {cols}")
    ingr_col = pick(cols, args.ingredient_col, INGR_CANDIDATES)
    form_col = pick(cols, None, FORM_CANDIDATES)

    # provenance에서 성분 사전 만들기 (medication_id로 연결이 1순위, 없으면 이름으로)
    ingr_by_key: dict[str, str] = {}
    ingr_by_mid: dict[str, str] = {}
    if args.provenance:
        prov = read_csv(args.provenance)
        pcols = list(prov[0].keys()) if prov else []
        p_name = pick(pcols, None, NAME_CANDIDATES)
        p_ingr = pick(pcols, args.ingredient_col, INGR_CANDIDATES)
        if not p_ingr:
            print(f"[경고] provenance에서 성분 컬럼을 못 찾았어요: {pcols}")
        else:
            for r in prov:
                ingr = (r.get(p_ingr) or "").strip()
                if not ingr:
                    continue
                if r.get("medication_id"):
                    ingr_by_mid[str(r["medication_id"]).strip()] = ingr
                if p_name and r.get(p_name):
                    ingr_by_key.setdefault(normalize_name(r[p_name]), ingr)
            if not ingr_by_mid and not ingr_by_key:
                print(f"[경고] provenance를 medication_id나 이름으로 연결하지 못했어요: {pcols}")

    groups: dict[str, dict] = defaultdict(lambda: {"names": set(), "count": 0, "ingr": "", "forms": set()})
    for r in meds:
        name = (r.get(name_col) or "").strip()
        key = normalize_name(name)
        if not key:
            continue
        g = groups[key]
        g["names"].add(name)
        g["count"] += 1
        ingr = (r.get(ingr_col) or "").strip() if ingr_col else ""
        mid = str(r.get("medication_id") or "").strip()
        g["ingr"] = g["ingr"] or ingr or ingr_by_mid.get(mid, "") or ingr_by_key.get(key, "") or bracket_text(name)
        if form_col and r.get(form_col):
            g["forms"].add(r[form_col].strip())

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 체크리스트 CSV (처방 많은 순 → 많이 나오는 약부터 채우기)
    rows = sorted(groups.items(), key=lambda kv: -kv[1]["count"])
    out_csv = DATA_DIR / "drug_checklist.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["순위", "key", "처방전 표기", "성분", "제형", "처방 건수", "의약품안전나라 검색", "완료"])
        for i, (key, g) in enumerate(rows, 1):
            first = sorted(g["names"])[0]
            w.writerow(
                [
                    i,
                    key,
                    " / ".join(sorted(g["names"])),
                    g["ingr"],
                    ",".join(sorted(g["forms"])),
                    g["count"],
                    NEDRUG_SEARCH + quote(first),
                    "",
                ]
            )

    # 2) drug_refs.json 틀 (이미 있으면 채운 내용 유지, 새 약만 추가)
    out_json = DATA_DIR / "drug_refs.json"
    existing = {}
    if out_json.exists():
        existing = {e["key"]: e for e in json.loads(out_json.read_text(encoding="utf-8"))["drugs"]}
    added = 0
    for key, g in rows:
        if key in existing:
            known = set(existing[key]["names"])
            existing[key]["names"] += sorted(g["names"] - known)
            continue
        existing[key] = empty_entry(key, sorted(g["names"])[0], g["ingr"], sorted(g["forms"]))
        existing[key]["names"] = sorted(g["names"])
        added += 1
    out_json.write_text(
        json.dumps({"version": 1, "drugs": list(existing.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    no_ingr = sum(1 for _, g in rows if not g["ingr"])
    print(f"약 {len(meds)}줄 → 제품 {len(rows)}개 (새로 추가 {added}개, 성분 비어 있음 {no_ingr}개)")
    print(f"체크리스트: {out_csv.relative_to(ROOT)}")
    print(f"틀: {out_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
