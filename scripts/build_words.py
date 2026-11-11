"""Build data/hsk3_words.json, hsk3_words.csv, data/levels/*,
data/hsk3_proper_nouns.json, data/hsk2_to_hsk3_changes.json and
data/review.csv from the official HSK syllabus query API dump.

English definitions and example sentences (data/content/*.jsonl) are
merged in when present, keyed by id; otherwise they stay null.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from opencc import OpenCC  # noqa: E402
from pypinyin import pinyin_dict  # noqa: E402

from lib import hsk2 as H  # noqa: E402
from lib import official as O  # noqa: E402
from lib import pinyin as P  # noqa: E402
from lib import pinyin_check as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "raw/official/chinesetest_glossary_api.json"
OUT_WORDS = ROOT / "data/hsk3_words.json"
OUT_CSV = ROOT / "data/hsk3_words.csv"
OUT_LEVELS = ROOT / "data/levels"
OUT_PROPER = ROOT / "data/hsk3_proper_nouns.json"
OUT_CHANGES = ROOT / "data/hsk2_to_hsk3_changes.json"
OUT_REVIEW = ROOT / "data/review.csv"
CONTENT_DIR = ROOT / "data/content"

S2T = OpenCC("s2t")  # s2t chosen over s2twp: character conversion only,
# no Taiwan vocabulary substitution; see SOURCES.md.

REVIEW_FIELDS = [
    "id",
    "no",
    "hanzi",
    "level",
    "official_pinyin",
    "pypinyin",
    "gf2021_pinyin",
    "issue_type",
    "note",
    "suggested",
    "status",
]

WORD_FIELDS = [
    "id",
    "no",
    "hanzi",
    "hanzi_official",
    "sense",
    "variants",
    "traditional",
    "pinyin",
    "pinyin_numbered",
    "level",
    "extra_levels",
    "pos",
    "pos_en",
    "pos_extra_en",
    "en",
    "example_zh",
    "example_pinyin",
    "example_en",
    "example_cloze",
    "hsk2_level",
    "gf2021_level",
    "change",
    "audio_word",
    "audio_example",
    "audio_word_voice_b",
    "source",
    "freq_rank",
    "topic_tags",
    "register",
    "tone_pattern",
    "tone_sandhi_surface",
    "has_neutral_tone",
    "has_erhua",
    "chars",
    "confusables",
    "review_flags",
]

ISSUE_TO_FLAG = {
    "disagreement": "pinyin_disagreement",
    "neutral_tone": "neutral_tone",
    "erhua": "erhua",
    "sandhi": "sandhi",
    "polyphone": "polyphone",
    "variant": "variant_pinyin",
    "other": "pinyin_other",
}

LEVEL_RANK = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, "7-9": 7}

CONTENT_KEYS = [
    "en",
    "example_zh",
    "example_pinyin",
    "example_en",
    "example_cloze",
    "topic_tags",
    "register",
]


def load_content():
    """Content files keyed by word id; empty dict when absent."""
    content = {}
    if CONTENT_DIR.is_dir():
        for f in sorted(CONTENT_DIR.glob("*.jsonl")):
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    wid = rec.get("id")
                    if wid:
                        content[wid] = rec
    return content


def build_words():
    api = O.load_api(API)
    words = [r for r in api if r["type"] == 1]
    proper = [r for r in api if r["type"] == 2]
    assert len(words) == 11000 and len(proper) == 231, (len(words), len(proper))

    gf = H.load_gf2021()
    clem, comp_old, conflicts = H.hsk2_conflicts()
    content = load_content()

    records = []
    review_rows = []
    dup_counts = Counter(O.clean_hanzi(r["word"])[0] for r in words)
    for r in words:
        hz, sense = O.clean_hanzi(r["word"])
        base_level, extra_levels = O.parse_level_name(r["levelName"])
        pos_en, pos_extra_en = O.split_pos(r.get("cixing"))
        parsed = P.align_pinyin(r["pinyin"], hz)
        syls = parsed["syllables"]

        rec = {
            "id": f"hsk3-{r['sort']:05d}",
            "no": r["sort"],
            "hanzi": hz,
            "hanzi_official": r["word"],
            "sense": sense,
            "variants": O.sense_variants(hz) if any(c in hz for c in "|/｜") else [],
            "traditional": S2T.convert(hz),
            "pinyin": r["pinyin"],
            "pinyin_numbered": parsed["numbered"],
            "level": base_level,
            "extra_levels": extra_levels,
            "pos": r.get("cixing"),
            "pos_en": pos_en,
            "pos_extra_en": pos_extra_en,
            "en": None,
            "example_zh": None,
            "example_pinyin": None,
            "example_en": None,
            "example_cloze": None,
            "hsk2_level": None,
            "gf2021_level": None,
            "change": None,
            "audio_word": None,
            "audio_example": None,
            "audio_word_voice_b": None,
            "source": "hsk-syllabus-2025",
            "freq_rank": None,
            "topic_tags": [],
            "register": None,
            "tone_pattern": P.tone_pattern(syls, hz),
            "tone_sandhi_surface": "-".join(
                str(t) for t in P.sandhi_surface(P.underlying_tones(syls, hz), syls, hz)
            ),
            "has_neutral_tone": any(s["tone"] == 5 for s in syls),
            "has_erhua": bool(syls and syls[-1].get("erhua")),
            "chars": list(dict.fromkeys(hz)),
            "confusables": [],
            "review_flags": [],
        }

        # hsk2 level: clem109 (complete 5000) primary, complete-old fallback
        h2 = clem.get(hz)
        h2b = comp_old.get(hz)
        if h2 is None and h2b is not None:
            h2 = h2b
        rec["hsk2_level"] = h2
        gf_rec = gf.get(hz)
        rec["gf2021_level"] = gf_rec["level"] if gf_rec else None

        lr = LEVEL_RANK[base_level]
        if h2 is None:
            rec["change"] = "new"
        elif lr > LEVEL_RANK[h2]:
            rec["change"] = "level_up"
        elif lr < LEVEL_RANK[h2]:
            rec["change"] = "level_down"
        else:
            rec["change"] = "same"
        if hz in conflicts:
            rec["review_flags"].append("hsk2_source_conflict")

        # merge content files when present
        c = content.get(rec["id"])
        if c:
            for k in CONTENT_KEYS:
                if k in c:
                    rec[k] = c[k]

        records.append(rec)

        # pinyin review rows
        gfp = gf_rec["pinyin"] if gf_rec else None
        rr = C.compare(
            {
                "id": rec["id"],
                "no": rec["no"],
                "hanzi": hz,
                "sense": sense,
                "multi": dup_counts[hz] if dup_counts[hz] > 1 else None,
                "level": base_level,
                "pinyin": r["pinyin"],
                "gf2021_pinyin": gfp,
            },
            parsed,
        )
        open_types = {row["issue_type"] for row in rr if row["status"] == "open"}
        for t in sorted(open_types):
            flag = ISSUE_TO_FLAG[t]
            if flag not in rec["review_flags"]:
                rec["review_flags"].append(flag)
        review_rows.extend(rr)

    # review.csv
    with open(OUT_REVIEW, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        for row in review_rows:
            w.writerow(row)

    # words.json
    OUT_WORDS.write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # words.csv (lists joined with '|', nested lists with ',')
    def csv_val(v):
        if v is None:
            return ""
        if isinstance(v, list):
            if v and isinstance(v[0], list):
                return "|".join(",".join(map(str, inner)) for inner in v)
            return "|".join(map(str, v))
        if isinstance(v, bool):
            return "true" if v else "false"
        return str(v)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(WORD_FIELDS)
        for rec in records:
            w.writerow([csv_val(rec[k]) for k in WORD_FIELDS])

    # per-level files
    OUT_LEVELS.mkdir(exist_ok=True)
    for name in ["1", "2", "3", "4", "5", "6", "7-9"]:
        level = int(name) if name.isdigit() else name
        subset = [r for r in records if r["level"] == level]
        (OUT_LEVELS / f"hsk3_level_{name}.json").write_text(
            json.dumps(subset, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        with open(OUT_LEVELS / f"hsk3_level_{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(WORD_FIELDS)
            for rec in subset:
                w.writerow([csv_val(rec[k]) for k in WORD_FIELDS])

    # proper nouns
    pn_records = [
        {
            "no": r["sort"],
            "hanzi": r["word"],
            "pinyin": None,  # the API gives no pinyin for the appendix
            "category": r.get("cixing"),
            "band": r["levelName"],
            "source": "hsk-syllabus-2025",
        }
        for r in proper
    ]
    OUT_PROPER.write_text(
        json.dumps(pn_records, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # change lists vs HSK 2.0
    def entry(rec):
        e = {"hanzi": rec["hanzi"], "level": rec["level"], "change": rec["change"]}
        if rec["sense"] is not None:
            e["sense"] = rec["sense"]
            e["id"] = rec["id"]
        if rec["hsk2_level"] is not None:
            e["hsk2_level"] = rec["hsk2_level"]
        return e

    changes = {}
    for key in ["new", "removed", "level_up", "level_down", "same"]:
        changes[key] = []
    removed = sorted((set(clem) | set(comp_old)) - {r["hanzi"] for r in records})
    for hz in removed:
        changes["removed"].append(
            {
                "hanzi": hz,
                "hsk2_level": clem.get(hz, comp_old.get(hz)),
            }
        )
    seen = set()
    for rec in records:
        key = (rec["hanzi"], rec["sense"])
        if key in seen:
            continue
        seen.add(key)
        if rec["change"] != "same" or rec["sense"] is not None:
            changes[rec["change"]].append(entry(rec))
        else:
            changes["same"].append(entry(rec))

    hsk2_counts = {
        "clem109_cumulative": {},
        "complete_old_cumulative": {},
        "official_2012": {1: 150, 2: 300, 3: 600, 4: 1200, 5: 2500, 6: 5000},
    }
    for lv in range(1, 7):
        hsk2_counts["clem109_cumulative"][lv] = sum(
            1 for v in clem.values() if v <= lv
        )
        hsk2_counts["complete_old_cumulative"][lv] = sum(
            1 for v in comp_old.values() if v <= lv
        )

    # GF 0025-2021 -> 2025 syllabus summary
    gf_words = set(gf)
    h3_words = {r["hanzi"] for r in records}
    gf_moves = {"same": [], "level_up": [], "level_down": [], "new": [], "removed": []}
    # one HSK3 level per word: base level of its lowest-no record
    h3_level = {}
    for rec in sorted(records, key=lambda r: r["no"]):
        h3_level.setdefault(rec["hanzi"], rec["level"])
    for hz in sorted(gf_words):
        gl = gf[hz]["level"]
        if hz not in h3_words:
            gf_moves["removed"].append({"hanzi": hz, "gf2021_level": gl})
            continue
        hl = h3_level[hz]
        e = {"hanzi": hz, "gf2021_level": gl, "hsk3_2025_level": hl}
        if LEVEL_RANK[hl] == LEVEL_RANK[gl]:
            gf_moves["same"].append(e)
        elif LEVEL_RANK[hl] > LEVEL_RANK[gl]:
            gf_moves["level_up"].append(e)
        else:
            gf_moves["level_down"].append(e)
    for hz in sorted(h3_words - gf_words):
        gf_moves["new"].append({"hanzi": hz, "hsk3_2025_level": h3_level[hz]})

    out_changes = {
        "hsk2_source_counts": hsk2_counts,
        "hsk2_source_conflicts": conflicts,
        "hsk2_to_hsk3_counts": {
            k: len(v)
            for k, v in changes.items()
        },
        "hsk2_to_hsk3_records": changes,
        "gf2021_to_2025_counts": {k: len(v) for k, v in gf_moves.items()},
        "gf2021_to_2025": gf_moves,
    }
    OUT_CHANGES.write_text(
        json.dumps(out_changes, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # summary to stderr
    lv_counts = Counter(r["level"] for r in records)
    ch_counts = Counter(r["change"] for r in records)
    it_counts = Counter((row["issue_type"], row["status"]) for row in review_rows)
    print("records", len(records), "proper nouns", len(pn_records))
    print("levels", dict(sorted(lv_counts.items(), key=lambda x: str(x[0]))))
    print("changes", dict(ch_counts))
    print("review rows by (issue_type, status):")
    for k, v in sorted(it_counts.items()):
        print("  ", k, v)


if __name__ == "__main__":
    build_words()
