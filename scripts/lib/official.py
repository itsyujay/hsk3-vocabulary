"""Parsing helpers for the official HSK syllabus query API records."""

import json
import re

_LEVEL_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七-九": "7-9"}

_POS_EN = {
    "名": "noun",
    "动": "verb",
    "形": "adjective",
    "副": "adverb",
    "量": "classifier",
    "连": "conjunction",
    "代": "pronoun",
    "助": "particle",
    "数": "numeral",
    "介": "preposition",
    "叹": "interjection",
    "拟声": "onomatopoeia",
    "前缀": "prefix",
    "后缀": "suffix",
    "数量": "numeral-classifier",
}

_LEVEL_NAME_RE = re.compile(r"(一|二|三|四|五|六|七-九)级")

OFFICIAL_TOTALS = {1: 300, 2: 200, 3: 500, 4: 1000, 5: 1600, 6: 1800, "7-9": 5600}


def load_api(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_level_name(level_name):
    """'一级（二级）（四级）' -> (1, [2, 4]); '七-九级' -> ('7-9', [])."""
    parts = _LEVEL_NAME_RE.findall(level_name)
    if not parts:
        raise ValueError(f"unparseable levelName {level_name!r}")
    base = _LEVEL_MAP[parts[0]]
    extras = [_LEVEL_MAP[p] for p in parts[1:]]
    return base, extras


def split_pos(cixing):
    """'形、（副）、（动）' -> (['adjective'], [['adverb'], ['verb']]).

    Parenthesized groups are the higher-level senses; they correspond one
    to one with the extra levels in levelName. A group may itself contain
    several codes ('（名、量）').
    Returns (pos_en, pos_extra_en); raw string is kept by the caller.
    """
    if not cixing:
        return [], []
    # split on 、 at parenthesis depth 0 only ('动、（名、量）')
    toks = []
    cur, depth = "", 0
    for ch in cixing.replace(" ", ""):
        if ch == "（":
            depth += 1
        elif ch == "）":
            depth -= 1
        if ch == "、" and depth == 0:
            if cur:
                toks.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        toks.append(cur)

    pos_en = []
    pos_extra = []
    pending = []
    for tok in toks:
        if tok.startswith("（") and tok.endswith("）"):
            inner = tok[1:-1]
            if pending:
                pos_en.extend(pending)
                pending = []
            pos_extra.append([_POS_EN[t] for t in inner.split("、") if t])
        else:
            pending.append(_POS_EN[tok])
    pos_en.extend(pending)
    return pos_en, pos_extra


def clean_hanzi(word):
    """'点1' -> '点'; sense digit stripped, returned separately."""
    m = re.match(r"^(.*?)(\d+)$", word)
    if m:
        return m.group(1), int(m.group(2))
    return word, None


def sense_variants(word_clean):
    """Split variant/slash/parenthesis forms ('爸爸|爸' -> ['爸爸', '爸'])."""
    out = re.split(r"[|/｜]", word_clean)
    return [v for v in (v.strip() for v in out) if v]
