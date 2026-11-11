"""HSK 2.0 (2012 Hanban) sources and change computation vs HSK 3.0 and
GF 0025-2021.

HSK 2.0 sources (both MIT, read-only clones):
- raw/hsk-vocabulary/hsk-vocab-json/hsk-level-{1..6}.json (clem109/hsk-vocabulary,
  cumulative ids 1..5000, from gigacool/hanyu-shuiping-kaoshi)
- raw/complete-hsk-vocabulary/wordlists/{inclusive,exclusive}/old/{1..6}.json
  (drkameleon/complete-hsk-vocabulary; its English meanings are CC-CEDICT and
  are never copied)
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _clean(word):
    """Strip sense digits and variant suffixes ('点1' -> '点')."""
    w = word.split("|")[0].split("/")[0].strip()
    while w and w[-1].isdigit():
        w = w[:-1]
    return w


def load_clem109():
    """{hanzi: level} from clem109 cumulative json lists."""
    out = {}
    for lv in range(1, 7):
        p = ROOT / f"raw/hsk-vocabulary/hsk-vocab-json/hsk-level-{lv}.json"
        for rec in json.load(open(p, encoding="utf-8")):
            hz = _clean(rec["hanzi"])
            if hz and hz not in out:
                out[hz] = lv
    return out


def load_complete_old():
    """{hanzi: level} from complete-hsk-vocabulary inclusive/old lists."""
    out = {}
    base = ROOT / "raw/complete-hsk-vocabulary/wordlists/inclusive/old"
    for lv in range(1, 7):
        for rec in json.load(open(base / f"{lv}.json", encoding="utf-8")):
            hz = _clean(rec["simplified"])
            if hz and hz not in out:
                out[hz] = lv
    return out


def hsk2_conflicts():
    """Words where the two sources disagree on level."""
    a = load_clem109()
    b = load_complete_old()
    conflicts = {}
    for hz in set(a) & set(b):
        if a[hz] != b[hz]:
            conflicts[hz] = {"clem109": a[hz], "complete_old": b[hz]}
    return a, b, conflicts


def load_gf2021():
    """{hanzi: {'level': int|'7-9', 'pinyin': str}} from raw/hsk30/hsk30.csv."""
    out = {}
    with open(ROOT / "raw/hsk30/hsk30.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hz = _clean(r["Simplified"])
            if not hz or hz in out:
                continue
            lv = r["Level"]
            out[hz] = {
                "level": lv if lv == "7-9" else int(lv),
                "pinyin": r["Pinyin"].split("|")[0].strip(),
            }
    return out


def load_gf2021_pos():
    """{hanzi: POS} from raw/hsk30/hsk30.csv (secondary POS reference)."""
    out = {}
    with open(ROOT / "raw/hsk30/hsk30.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hz = _clean(r["Simplified"])
            if hz and hz not in out and r.get("POS"):
                out[hz] = r["POS"]
    return out
