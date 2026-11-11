"""Build data/hsk3_chars.json: one record per distinct character in the
11,000 syllabus words, with official 认读字/手写 levels from the 2025
syllabus mirror (raw/ofou-hsk) and radical + stroke count from Unihan.

Component, etymology, hint and frequency fields are written as null.
"""

import csv
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import official as O  # noqa: E402
from lib import pinyin as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/hsk3_chars.json"
UNIHAN_ZIP = ROOT / "raw/unihan/Unihan.zip"

# Kangxi radical number -> additional strokes 0 representative is derived
# from Unihan itself (the char with 0 residual strokes in its own radical).


def load_unihan():
    """{codepoint: {'rs': 'rad.strokes', 'total': n}} from Unihan.zip."""
    info = defaultdict(dict)
    fields = {"kRSUnicode", "kTotalStrokes"}
    with zipfile.ZipFile(UNIHAN_ZIP) as z:
        for name in z.namelist():
            with z.open(name) as f:
                for raw in f:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) != 3 or parts[1] not in fields:
                        continue
                    cp = int(parts[0][2:], 16)
                    if parts[1] == "kRSUnicode":
                        # '85.2' or multiple space-separated variants
                        info[cp]["rs"] = parts[2].split(" ")[0]
                    else:
                        info[cp]["total"] = int(parts[2].split(" ")[0])
    return info


def load_ofou_levels():
    char_level = {}
    writing_level = {}
    with open(ROOT / "raw/ofou-hsk/汉字.csv", encoding="utf-8") as f:
        for r in csv.reader(f):
            if r[0] == "No.":
                continue
            char_level[r[2]] = r[1]
    with open(ROOT / "raw/ofou-hsk/手写汉字.csv", encoding="utf-8") as f:
        for r in csv.reader(f):
            if r[0] == "No.":
                continue
            writing_level[r[2]] = r[1]
    return char_level, writing_level


def main():
    words = json.load(open(ROOT / "data/hsk3_words.json", encoding="utf-8"))

    # per char: ids, words, and readings from the aligned official pinyin.
    # In erhua words the trailing 儿 has no syllable of its own, so its
    # reading list only collects words where 儿 is pronounced as a syllable.
    ids = defaultdict(list)
    words_for = defaultdict(list)
    readings = defaultdict(list)
    for rec in words:
        hz = rec["hanzi"]
        for ch in dict.fromkeys(hz):
            ids[ch].append(rec["id"])
            words_for[ch].append(rec["hanzi"])
        parsed = P.align_pinyin(rec["pinyin"], hz)
        for syl in parsed["syllables"]:
            ci = syl.get("char_index")
            if ci is None or ci >= len(hz):
                continue
            ch = hz[ci]
            if syl["text"] not in readings[ch]:
                readings[ch].append(syl["text"])

    char_level, writing_level = load_ofou_levels()
    unihan = load_unihan()

    # radical representatives: the char with 0 residual strokes of its own.
    # kRSUnicode radical numbers may carry a quote mark for variant
    # radical forms (e.g. "120'.3"); strip it.
    def parse_rs(rs):
        rad, _, rest = rs.partition(".")
        rad = int("".join(c for c in rad if c.isdigit()))
        return rad, int(rest) if rest else 0

    radical_char = {}
    for cp, d in unihan.items():
        rs = d.get("rs")
        if not rs:
            continue
        rad, rest = parse_rs(rs)
        if rest < 0:
            continue  # extension ideographs can carry negative residuals
        best = radical_char.get(rad)
        if (
            best is None
            or rest < best[1]
            or (rest == best[1] and cp < ord(best[0]))
        ):
            radical_char[rad] = (chr(cp), rest)

    records = []
    missing_unihan = []
    for ch in sorted(ids, key=lambda c: ord(c)):
        cp = ord(ch)
        u = unihan.get(cp)
        rad = stroke = None
        if u:
            rs = u.get("rs")
            if rs:
                rad = radical_char.get(parse_rs(rs)[0], (None,))[0]
            stroke = u.get("total")
        else:
            missing_unihan.append(ch)
        records.append(
            {
                "char": ch,
                "pinyin": readings.get(ch, []),
                "char_level": char_level.get(ch),
                "writing_level": writing_level.get(ch),
                "ids": None,
                "word_ids": ids[ch],
                "components": None,
                "radical": rad,
                "stroke_count": stroke,
                "etymology_type": None,
                "semantic_component": None,
                "phonetic_component": None,
                "hint_en": None,
                "char_freq_rank": None,
                "words": words_for[ch],
            }
        )

    OUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("chars:", len(records))
    print("distinct chars in words:", len(ids))
    print("ofou 认读字 coverage:",
          sum(1 for r in records if r["char_level"]), "/ 3088 official")
    print("手写字 coverage:", sum(1 for r in records if r["writing_level"]),
          "/ 1200 official")
    print("missing from Unihan:", len(missing_unihan), missing_unihan[:10])
    print("no radical:", sum(1 for r in records if r["radical"] is None))
    print("no stroke count:", sum(1 for r in records if r["stroke_count"] is None))
    # chars not covered by the 认读字 list (mostly L7-9 vocabulary)
    uncovered = [r["char"] for r in records if r["char_level"] is None]
    print("chars without official reading level:", len(uncovered),
          "".join(uncovered[:80]))


if __name__ == "__main__":
    main()
