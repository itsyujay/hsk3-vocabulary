"""Validate the built HSK 3.0 dataset.

Checks:
- per-level record counts vs official totals (300/200/500/1000/1600/1800/5600)
  and 231 proper nouns;
- unique word ids;
- no empty hanzi/pinyin;
- pinyin_numbered round-trips to the official pinyin;
- every character referenced in a word exists in hsk3_chars.json and every
  char record references existing word ids;
- all review.csv ids exist in the word dataset.

Exits non-zero on failure; prints a summary table.
"""

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import official as O  # noqa: E402
from lib import pinyin as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_TOTALS = {1: 300, 2: 200, 3: 500, 4: 1000, 5: 1600, 6: 1800, "7-9": 5600}
REVIEW_FIELDS = [
    "id", "no", "hanzi", "level", "official_pinyin", "pypinyin",
    "gf2021_pinyin", "issue_type", "note", "suggested", "status",
]


def check_dist(errors, check, word_ids, lv_counter, chars, review_rows):
    """Verify dist/ against its manifest (hashes, sizes, counts)."""
    manifest_path = ROOT / "dist/manifest.json"
    if not manifest_path.exists():
        errors.append("dist/manifest.json missing (run scripts/build_dist.py)")
        return
    m = json.load(open(manifest_path, encoding="utf-8"))
    for key in ("schema_version", "data_version", "generated_at", "source", "counts", "files"):
        check(key in m, f"manifest missing key {key}")
    check(re.fullmatch(r"\d+\.\d+\.\d+", m.get("schema_version", "")) is not None,
          "manifest schema_version not semver")
    check("pdf_sha256" in m.get("source", {}), "manifest source lacks pdf_sha256")

    for rel, meta in m.get("files", {}).items():
        p = ROOT / "dist" / rel
        if not check(p.exists(), f"dist/{rel} missing"):
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        check(h == meta["sha256"], f"dist/{rel} sha256 mismatch")
        check(p.stat().st_size == meta["bytes"], f"dist/{rel} byte size mismatch")
        if rel.endswith(".json"):
            data = json.load(open(p, encoding="utf-8"))
            n = len(data) if isinstance(data, list) else 0
            if "hsk2_to_hsk3_changes" in rel:
                n = sum(len(v) for v in data.get("hsk2_to_hsk3_records", {}).values())
                n += sum(len(v) for v in data.get("gf2021_to_2025", {}).values())
            check(n == meta["records"], f"dist/{rel} record count {n} != manifest {meta['records']}")
        elif rel.endswith(".csv"):
            with open(p, encoding="utf-8") as f:
                n = sum(1 for _ in csv.reader(f)) - 1
            check(n == meta["records"], f"dist/{rel} record count {n} != manifest {meta['records']}")

    # dist contents must match data/
    dw = json.load(open(ROOT / "dist/hsk3_words.json", encoding="utf-8"))
    check(len(dw) == 11000, f"dist words {len(dw)} != 11000")
    check({r["id"] for r in dw} == word_ids, "dist words ids differ from data")
    for level, want in OFFICIAL_TOTALS.items():
        check(
            sum(1 for r in dw if r["level"] == level) == want,
            f"dist level {level} count mismatch",
        )
    dc = json.load(open(ROOT / "dist/hsk3_chars.json", encoding="utf-8"))
    check(len(dc) == len(chars), "dist chars count differs from data")
    dn = json.load(open(ROOT / "dist/hsk3_proper_nouns.json", encoding="utf-8"))
    check(len(dn) == 231, "dist proper nouns != 231")
    with open(ROOT / "dist/review.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    check(list(rows[0].keys()) == REVIEW_FIELDS if rows else True,
          "dist review.csv columns changed")
    check(len(rows) == review_rows, "dist review row count differs from data")
    counts = m.get("counts", {})
    for level, want in OFFICIAL_TOTALS.items():
        check(counts.get(f"level_{level}") == want, f"manifest level_{level} count wrong")


def main():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)
        return cond

    words = json.load(open(ROOT / "data/hsk3_words.json", encoding="utf-8"))
    proper = json.load(open(ROOT / "data/hsk3_proper_nouns.json", encoding="utf-8"))
    chars = json.load(open(ROOT / "data/hsk3_chars.json", encoding="utf-8"))

    check(len(words) == 11000, f"expected 11,000 words, got {len(words)}")
    check(len(proper) == 231, f"expected 231 proper nouns, got {len(proper)}")

    ids = [r["id"] for r in words]
    id_set = set(ids)
    dup = [i for i, n in Counter(ids).items() if n > 1]
    check(not dup, f"duplicate ids: {dup[:5]}")
    check(
        all(re.fullmatch(r"hsk3-\d{5}", i) for i in ids),
        "ids not of form hsk3-NNNNN",
    )
    check(
        all(r["no"] == int(r["id"].split("-")[1]) for r in words),
        "no does not match id serial",
    )
    empty_hz = [r["id"] for r in words if not r["hanzi"].strip()]
    check(not empty_hz, f"empty hanzi: {empty_hz[:5]}")
    empty_py = [r["id"] for r in words if not r["pinyin"].strip()]
    check(not empty_py, f"empty pinyin: {empty_py[:5]}")

    # pinyin_numbered round-trips
    rt_fail = []
    for r in words:
        try:
            ns = r["pinyin_numbered"]
            if P.roundtrip_mismatch(ns, r["pinyin"]):
                rt_fail.append((r["id"], r["pinyin"], ns))
        except Exception:
            rt_fail.append((r["id"], r["pinyin"], r["pinyin_numbered"]))
    check(not rt_fail, f"pinyin_numbered round-trip failures: {rt_fail[:5]}")

    # levels
    lv = Counter(r["level"] for r in words)
    for level, want in OFFICIAL_TOTALS.items():
        check(
            lv[level] == want,
            f"level {level}: {lv[level]} records, official {want}",
        )

    # change field consistency
    ch = Counter(r["change"] for r in words)
    check(
        set(ch) == {"new", "removed", "level_up", "level_down", "same"} - {"removed"},
        f"unexpected change values: {set(ch)}",
    )
    bad_change = [
        r["id"]
        for r in words
        if (r["hsk2_level"] is None) != (r["change"] == "new")
    ]
    check(not bad_change, f"change/hsk2_level inconsistency: {bad_change[:5]}")

    # per-level files mirror the main dataset
    for name in ["1", "2", "3", "4", "5", "6", "7-9"]:
        p = ROOT / f"data/levels/hsk3_level_{name}.json"
        sub = json.load(open(p, encoding="utf-8"))
        level = int(name) if name.isdigit() else name
        check(
            all(r["level"] == level for r in sub),
            f"level file {name} contains other levels",
        )
        check(
            len(sub) == OFFICIAL_TOTALS[level],
            f"level file {name} count {len(sub)} != {OFFICIAL_TOTALS[level]}",
        )
        csv_path = ROOT / f"data/levels/hsk3_level_{name}.csv"
        rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
        check(
            len(rows) == len(sub) and [x["id"] for x in rows] == [x["id"] for x in sub],
            f"level file {name} csv/json mismatch",
        )

    # characters
    char_set = {c["char"] for c in chars}
    referenced = set()
    for r in words:
        for c in r["chars"]:
            referenced.add(c)
    missing = sorted(referenced - char_set)
    check(not missing, f"chars referenced by words but missing from chars file: {missing[:10]}")
    word_ids = id_set
    bad_ids = []
    for c in chars:
        for wid in c["ids"]:
            if wid not in word_ids:
                bad_ids.append((c["char"], wid))
    check(not bad_ids, f"char ids referencing unknown words: {bad_ids[:5]}")
    check(len(chars) == len(referenced), f"chars file size {len(chars)} != referenced {len(referenced)}")

    # review.csv ids exist
    review_rows = 0
    review_ids = set()
    with open(ROOT / "data/review.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            review_rows += 1
            review_ids.add(row["id"])
    unknown = sorted(review_ids - id_set)
    check(not unknown, f"review.csv ids not in dataset: {unknown[:5]}")

    # dist/ release artifacts vs manifest
    check_dist(errors, check, id_set, lv, chars, review_rows)

    # summary table
    print()
    print(f"{'check':44s} {'value':>10s}")
    print("-" * 56)
    rows = [
        ("words", len(words)),
        ("proper nouns", len(proper)),
        ("distinct chars", len(chars)),
        ("review rows", review_rows),
    ]
    for level, want in OFFICIAL_TOTALS.items():
        rows.append((f"level {level} (official {want})", lv[level]))
    for k, v in rows:
        print(f"{k:44s} {v!s:>10s}")
    print("-" * 56)
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
