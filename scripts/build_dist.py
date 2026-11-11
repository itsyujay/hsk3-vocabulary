"""Assemble dist/: stable versioned release artifacts for the website repo.

Copies the built dataset files from data/ into dist/ and writes
dist/manifest.json with schema/data versions, source info, per-level
counts and per-file sha256 + byte size + record counts.

Usage: build_dist.py [--data-version YYYY.M.B]
data_version defaults to the current UTC date with build number 0;
bump the build number for same-month rebuilds.
"""

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

SCHEMA_VERSION = "1.0.0"
OFFICIAL_TOTALS = {1: 300, 2: 200, 3: 500, 4: 1000, 5: 1600, 6: 1800, "7-9": 5600}

SOURCE = {
    "name": "《中文水平考试 HSK 考试大纲》 (CLEC, released 2025-11, in force 2026-07)",
    "api_url": "https://www.chinesetest.cn/api/hsk/outline/glossaryPage (official query API behind https://www.chinesetest.cn/syllabus, mirrored at raw/official/chinesetest_glossary_api.json)",
    "pdf_sha256": "ec74ce0439e837bbb15154be13e747ae798903b2fd3a331629df6c3b45504941",
    "sources_doc": "SOURCES.md",
}

FILES = [
    "hsk3_words.json",
    "hsk3_words.csv",
    "hsk3_chars.json",
    "hsk3_proper_nouns.json",
    "hsk2_to_hsk3_changes.json",
    "review.csv",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_count(rel):
    p = DIST / rel
    if rel.endswith(".json"):
        data = json.load(open(p, encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if "hsk2_to_hsk3_changes" in rel:
            return sum(
                len(v) for v in data.get("hsk2_to_hsk3_records", {}).values()
            ) + sum(len(v) for v in data.get("gf2021_to_2025", {}).values())
        return 0
    with open(p, encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--data-version",
        default=datetime.now(timezone.utc).strftime("%Y.%m") + ".0",
    )
    args = ap.parse_args()

    if not (ROOT / "data/hsk3_words.json").exists():
        sys.exit("run scripts/build_words.py and scripts/build_chars.py first")

    DIST.mkdir(exist_ok=True)
    (DIST / "levels").mkdir(exist_ok=True)

    for name in FILES:
        shutil.copy2(ROOT / "data" / name, DIST / name)
    for p in (ROOT / "data/levels").glob("*"):
        shutil.copy2(p, DIST / "levels" / p.name)
    schema_src = DIST / "SCHEMA.md"
    if not schema_src.exists():
        sys.exit("dist/SCHEMA.md missing")

    words = json.load(open(DIST / "hsk3_words.json", encoding="utf-8"))
    chars = json.load(open(DIST / "hsk3_chars.json", encoding="utf-8"))
    proper = json.load(open(DIST / "hsk3_proper_nouns.json", encoding="utf-8"))
    counts = {"total": len(words), "chars": len(chars), "proper_nouns": len(proper)}
    for level, want in OFFICIAL_TOTALS.items():
        n = sum(1 for r in words if r["level"] == level)
        assert n == want, (level, n, want)
        counts[f"level_{level}"] = n

    files = {}
    for rel in FILES + [
        f"levels/hsk3_level_{n}.{ext}"
        for n in ["1", "2", "3", "4", "5", "6", "7-9"]
        for ext in ["json", "csv"]
    ]:
        p = DIST / rel
        files[rel] = {
            "sha256": sha256(p),
            "bytes": p.stat().st_size,
            "records": record_count(rel),
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "data_version": args.data_version,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source": SOURCE,
        "counts": counts,
        "files": files,
    }
    (DIST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("dist/ written:", len(files) + 2, "files")
    print("schema_version", SCHEMA_VERSION, "data_version", args.data_version)


if __name__ == "__main__":
    main()
