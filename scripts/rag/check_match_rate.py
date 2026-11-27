"""검증: 약 목록 전체를 실제 가이드와 같은 경로(normalize_medication → build_references)로 넣어
몇 %가 참조 정보를 찾는지 본다.

    uv run python scripts/rag/check_match_rate.py --medication data/sample/medication.csv
    uv run python scripts/rag/check_match_rate.py --medication data/sample/medication_from_ocr.csv  # OCR 결과 약 이름

못 찾은 약 목록 = 다음에 drug_refs.json에서 채울 약.
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.services.guide.drug_reference import build_references_with_report  # noqa: E402
from app.services.guide.service import normalize_medication  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--medication", required=True, type=Path)
    ap.add_argument("--name-col", default="name")
    args = ap.parse_args()

    with args.medication.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    meds = [
        normalize_medication(
            {
                "medication_id": int(r.get("medication_id") or i),
                "name": r.get(args.name_col),
                "ingredient": r.get("ingredient"),
                "insurance_code": r.get("insurance_code"),
            }
        )
        for i, r in enumerate(rows, 1)
    ]
    _, report = build_references_with_report(meds)

    by_method = Counter(m.method for m in report)
    found = len(report) - by_method["none"]
    print(f"참조 정보 적중률: {found}/{len(report)} = {found / len(report):.0%}")
    for method in ["insurance", "exact", "fuzzy", "permit_ingredient", "ingredient", "none"]:
        print(f"  {method:<17} {by_method[method]}")

    fuzzy = [m for m in report if m.method == "fuzzy"]
    if fuzzy:
        print("\n[비슷한 이름으로 연결됨 — 맞는지 눈으로 확인]")
        for m in sorted({(m.name, m.key, m.score) for m in fuzzy}):
            print(f"  {m[0]} → {m[1]} ({m[2]})")

    missing = Counter(m.name for m in report if m.method == "none")
    if missing:
        print("\n[못 찾은 약 — 처방 많은 순]")
        for name, n in missing.most_common():
            print(f"  {n:>3}건  {name}")


if __name__ == "__main__":
    main()
