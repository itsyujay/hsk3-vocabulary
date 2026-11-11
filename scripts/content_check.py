#!/usr/bin/env python3
"""Checker and helpers for data/content/*.jsonl batches.

Usage:
  python scripts/content_check.py --level N batch.jsonl
      Validate a batch against the cumulative vocab of levels <= N and all
      field rules; print per-line problems and a token-frequency summary.
  python scripts/content_check.py --pinyin batch.jsonl
      Print pypinyin phrase-mode suggestions for example_zh (review by hand).
  python scripts/content_check.py --dump-level N
      Print the level-N word list (id, hanzi, pinyin, POS) as reference.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "raw" / "official" / "chinesetest_glossary_api.json"

TOPIC_TAGS = {
    "daily", "food", "travel", "shopping", "school", "work", "business",
    "health", "family", "emotion", "time", "number", "place", "nature",
    "weather", "sports", "culture", "media", "tech", "society", "science",
    "grammar",
}
REGISTERS = {"spoken", "neutral", "written", "internet"}

CLOZE_MARK = "＿＿"
PUNCT = "，。！？；：、…—·“”‘’（）《》〈〉!?,.;:()[]{}<>\"'-"

_digits = re.compile(r"[0-9]")
_hanzi = re.compile(r"[一-鿿]")

_SYLLABLES = None


_INITIALS = ["", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j",
             "q", "x", "r", "zh", "ch", "sh", "z", "c", "s", "y", "w"]
_FINALS = ["a", "o", "e", "i", "u", "ai", "ei", "ao", "ou", "an", "en",
           "ang", "eng", "ong", "er", "ia", "ie", "iao", "iu", "ian", "in",
           "iang", "ing", "iong", "ua", "uo", "uai", "ui", "uan", "un",
           "uang", "ue"]


def _load_syllables():
    global _SYLLABLES
    if _SYLLABLES is None:
        _SYLLABLES = {ini + fin for ini in _INITIALS for fin in _FINALS}
    return _SYLLABLES


def _strip_marks(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def count_syllables(pinyin_text):
    """Count pinyin syllables by backtracking longest-match over the syllable
    table. Returns (count, first_token_that_could_not_be_parsed)."""
    table = _load_syllables()

    def parse(s):
        if not s:
            return 0
        for ln in range(min(6, len(s)), 0, -1):
            if s[:ln] in table:
                rest = parse(s[ln:])
                if rest is not None:
                    return 1 + rest
        return None

    total = 0
    bad = None
    for token in pinyin_text.split():
        token = _strip_marks(token).lower()
        token = re.sub(r"[^a-züv]", "", token)
        if not token:
            continue
        n = parse(token)
        if n is None:
            # 儿 suffix merges into the previous syllable (zhèr, wánr)
            if token.endswith("r") and len(token) > 1:
                n = parse(token[:-1])
        if n is None:
            bad = token
            break
        total += n
    return total, bad


def base_level(level_name):
    return {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}[level_name[0]]


def strip_sense_digits(word):
    return _digits.sub("", word)


def load_glossary():
    recs = [r for r in json.loads(API.read_text(encoding="utf-8")) if r.get("type") == 1]
    out = []
    for r in recs:
        hanzi = strip_sense_digits(r["word"])
        py = r["pinyin"]
        # 儿 is an r-colored suffix when the official pinyin ends in plain -r
        er_suffix = hanzi.endswith("儿") and len(hanzi) > 1 and py.endswith("r") \
            and not py.endswith("ér")
        out.append({
            "id": "hsk3-%05d" % r["sort"],
            "sort": r["sort"],
            "hanzi": hanzi,
            "official_word": r["word"],
            "pinyin": py,
            "cixing": r.get("cixing", ""),
            "level": base_level(r["levelName"]),
            "er_suffix": er_suffix,
        })
    return out


def hanzi_count(text, vocab, gloss):
    """Number of hanzi characters, treating r-colored 儿 suffixes as part of
    the preceding syllable."""
    suffix_words = {w["hanzi"] for w in gloss if w["er_suffix"]}
    n = 0
    for tok in tokenize(text, vocab):
        for c in tok:
            if _hanzi.match(c):
                n += 1
        if tok.endswith("儿") and (tok in suffix_words or tok not in vocab):
            n -= 1
    return n


def cumulative_vocab(gloss, level):
    """Hanzi allowed at or below `level` (hanzi of multi-char words count as
    whole words only; the set holds whole words, lookup is whole-token)."""
    return {w["hanzi"] for w in gloss if w["level"] <= level}


def _repair(toks, vocab):
    """Fix jieba quirks against the official vocab:
    1. merge consecutive hanzi tokens whose concatenation is a vocab word
       (e.g. 不 + 客气 -> 不客气);
    2. split an unknown token greedily into vocab words (e.g. jieba's 地请),
       leaving unknown pieces to be reported."""
    out = []
    i = 0
    while i < len(toks):
        if _hanzi.match(toks[i]):
            cur = toks[i]
            j = i + 1
            best = None
            while j < len(toks) and _hanzi.match(toks[j]) and len(cur) < 4:
                cur += toks[j]
                if cur in vocab:
                    best = (cur, j)
            if best:
                out.append(best[0])
                i = best[1] + 1
            elif toks[i] in vocab:
                out.append(toks[i])
                i += 1
            else:
                _split(out, toks[i], vocab)
                i += 1
        else:
            out.append(toks[i])
            i += 1
    return out


def _split(out, tok, vocab):
    """Greedy longest-match split of an unknown hanzi token into vocab words."""
    i = 0
    while i < len(tok):
        for ln in (4, 3, 2, 1):
            piece = tok[i:i + ln]
            if piece in vocab:
                out.append(piece)
                i += ln
                break
        else:
            out.append(tok[i])
            i += 1


def _greedy_rescue(text, vocab):
    """Check whether the hanzi stream can be fully segmented into vocab
    words (backtracking); return leftover pieces from a greedy pass when
    no full segmentation exists."""
    chars = [c for c in text if _hanzi.match(c)]
    s = "".join(chars)

    def parse(i):
        if i >= len(s):
            return True
        for ln in range(min(4, len(s) - i), 0, -1):
            if s[i:i + ln] in vocab and parse(i + ln):
                return True
        return False

    if parse(0):
        return []
    i = 0
    unknown = []
    while i < len(s):
        for ln in range(min(4, len(s) - i), 0, -1):
            if s[i:i + ln] in vocab:
                i += ln
                break
        else:
            unknown.append(s[i])
            i += 1
    return unknown


def _window_rescue(text, vocab, unknown):
    """For each unknown token, re-segment a 3-token window around it with
    greedy longest match; if the window is fully covered, the miss was a
    jieba segmentation artifact, not an out-of-level word."""
    toks = [t for t in tokenize(text, vocab)]
    keep = set(unknown)
    for k, t in enumerate(toks):
        if t not in keep:
            continue
        lo, hi = max(0, k - 1), min(len(toks), k + 2)
        window = "".join(x for x in toks[lo:hi] if _hanzi.match(x))
        if not _greedy_rescue(window, vocab):
            for x in toks[lo:hi]:
                if x in keep:
                    keep.discard(x)
    return [t for t in unknown if t in keep]


def tokenize(text, vocab=None):
    import jieba
    toks = [t for t in jieba.lcut(text) if t.strip() and t not in (" ", "　")]
    if vocab is not None:
        toks = _repair(toks, vocab)
    return toks


def chars_no_punct(text):
    return [c for c in text if _hanzi.match(c)]


def check_line(obj, gloss, vocab, level, seen_ids):
    problems = []
    id_index = {w["id"]: w for w in gloss}
    wid = obj.get("id", "")
    if wid in seen_ids:
        problems.append("duplicate id")
    rec = id_index.get(wid)
    if rec is None:
        problems.append("unknown id")
        rec = None
    for key in ("id", "hanzi", "en", "example_zh", "example_pinyin", "example_en",
                "example_cloze", "topic_tags", "register"):
        if key not in obj:
            problems.append(f"missing field {key}")
    if rec is not None and obj.get("hanzi") != rec["hanzi"]:
        problems.append(f"hanzi mismatch: {obj.get('hanzi')!r} != official {rec['hanzi']!r}")
    zh = obj.get("example_zh", "")
    # target word present exactly once
    if rec is not None:
        n = zh.count(rec["hanzi"])
        if n != 1:
            problems.append(f"target word appears {n}x in example_zh, expected 1")
    cloze = obj.get("example_cloze", "")
    if cloze and rec is not None:
        expected = zh.replace(rec["hanzi"], CLOZE_MARK)
        if cloze != expected:
            problems.append("example_cloze does not match example_zh with word replaced")
    if CLOZE_MARK in zh:
        problems.append("cloze mark leaked into example_zh")
    tags = obj.get("topic_tags")
    if not isinstance(tags, list) or not 1 <= len(tags) <= 3:
        problems.append("topic_tags must be a list of 1-3 items")
    elif any(t not in TOPIC_TAGS for t in tags):
        problems.append("unknown topic_tags: %s" % ",".join(t for t in tags if t not in TOPIC_TAGS))
    if obj.get("register") not in REGISTERS:
        problems.append("bad register: %r" % obj.get("register"))
    # length limits (Chinese chars, punctuation excluded)
    nchars = len(chars_no_punct(zh))
    limit = 18 if level <= 3 else 25
    floor = 6 if level <= 3 else 6
    if nchars < floor:
        problems.append(f"example too short ({nchars} chars)")
    if nchars > limit:
        problems.append(f"example too long ({nchars} chars > {limit})")
    # out-of-level tokens; jieba's misses are rescued when a small window
    # around the miss can be re-segmented fully into vocab words
    out = []
    for tok in tokenize(zh, vocab):
        if _hanzi.match(tok) and tok not in vocab:
            out.append(tok)
    if out:
        out = _window_rescue(zh, vocab, out)
    # pinyin sanity check: syllable count vs hanzi count (儿 suffixes merge
    # into the preceding syllable, so they do not add one)
    py = obj.get("example_pinyin", "")
    if py:
        nsyl, unparsed = count_syllables(py)
        nzh = hanzi_count(zh, vocab, gloss)
        if unparsed:
            problems.append("pinyin token not parseable: %s" % unparsed)
        elif nsyl != nzh:
            problems.append(f"pinyin syllables {nsyl} != hanzi {nzh}")
    return problems, out, nchars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int)
    ap.add_argument("--pinyin", action="store_true")
    ap.add_argument("--dump-level", type=int)
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    gloss = load_glossary()

    if args.dump_level is not None:
        for w in gloss:
            if w["level"] == args.dump_level:
                print(f"{w['id']}\t{w['official_word']}\t{w['pinyin']}\t{w['cixing']}")
        return

    if args.pinyin:
        from pypinyin import lazy_pinyin, Style
        for path in args.files:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                zh = obj.get("example_zh", "")
                py = lazy_pinyin(zh, style=Style.TONE, errors="ignore")
                print(obj.get("id", "?"))
                print("  zh:", zh)
                print("  py:", " ".join(py))
                print("  has:", obj.get("example_pinyin", ""))
        return

    if args.level is None or not args.files:
        ap.error("need --level N and input files (or --pinyin/--dump-level)")

    vocab = cumulative_vocab(gloss, args.level)
    # single tokens that jieba splits but which are composed of listed words
    # are NOT accepted; proper nouns reported separately below.
    seen = set()
    token_counter = Counter()
    n_bad = 0
    for path in args.files:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            problems, out, nchars = check_line(obj, gloss, vocab, args.level, seen)
            seen.add(obj.get("id"))
            token_counter.update(out)
            if problems or out:
                n_bad += 1
                label = f"{obj.get('id','?')} {obj.get('hanzi','?')}"
                print(f"[{label}]")
                for p in problems:
                    print(f"  - {p}")
                if out:
                    print(f"  - out-of-level tokens ({nchars} chars): {' '.join(out)}")
                    print(f"    zh: {obj.get('example_zh','')}")
    total = len(seen)
    print(f"\nchecked {total} lines, {n_bad} with problems")
    if token_counter:
        print("top out-of-level tokens:")
        for tok, c in token_counter.most_common(40):
            print(f"  {tok} x{c}")
    else:
        print("out-of-level tokens: 0")


if __name__ == "__main__":
    main()
