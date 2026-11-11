# hsk3-vocabulary

Structured vocabulary data for the new HSK (HSK 3.0), based on the official
《中文水平考试 HSK 考试大纲》 (released 2025-11, used from the 2026-12-13 exam).

## Contents

- 11,000 syllabus words: L1 300, L2 200, L3 500, L4 1,000, L5 1,600, L6 1,800, L7-9 5,600
- 231 proper nouns from the syllabus appendix
- 3,088 characters with official reading and writing levels, radical and stroke count
- Official pinyin and part of speech, traditional forms, tone patterns and spoken tone-sandhi forms
- HSK 2.0 level and GF 0025-2021 level for each word, with change summaries
- English definitions and example sentences (with pinyin, translation and cloze form), being filled level by level
- `review.csv`: pinyin points worth a second look (polyphones, neutral tones, erhua, tone sandhi, source disagreements)

## Files

Release files are in `dist/` and are described in `dist/SCHEMA.md`.
`dist/manifest.json` lists the schema version, data version, record counts and
sha256 of every file.

| File | Records |
|---|---|
| `dist/hsk3_words.json` / `.csv` | 11,000 words |
| `dist/levels/hsk3_level_{1..6,7-9}.json` / `.csv` | words of one level |
| `dist/hsk3_chars.json` | 3,088 characters |
| `dist/hsk3_proper_nouns.json` | 231 proper nouns |
| `dist/hsk2_to_hsk3_changes.json` | HSK 2.0 to HSK 3.0 changes |
| `dist/review.csv` | pinyin review list |

## Build

```
python scripts/build_words.py
python scripts/build_chars.py
python scripts/build_dist.py --data-version YYYY.MM.N
python scripts/validate.py
```

`validate.py` checks per-level counts against the official totals, ids,
pinyin round-trips and the release manifest.

## Sources

See `SOURCES.md` for the sources used and their licenses.

## License

- **Data** (word list, pinyin, definitions, example sentences and all files in `data/` and `dist/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see `LICENSE`.
- **Code** (`scripts/`): MIT, see `LICENSE-CODE`.
- **Audio** (distributed separately from this repository): [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), see `LICENSE-AUDIO`. Audio was generated with text-to-speech; it is synthetic, not a human recording.

## How to cite

Plain text:

> Yujay. *hsk3-vocabulary: HSK 3.0 vocabulary dataset* (version as listed in `dist/manifest.json`). 2026. <SITE_URL>. Licensed under CC BY 4.0. Word list from 中外语言交流合作中心, 《中文水平考试 HSK 考试大纲》, 2025.

BibTeX:

```bibtex
@misc{hsk3vocabulary2026,
  author       = {Yujay},
  title        = {hsk3-vocabulary: {HSK} 3.0 vocabulary dataset},
  year         = {2026},
  howpublished = {\url{<SITE_URL>}},
  note         = {Version as listed in dist/manifest.json. Licensed under CC BY 4.0. Word list from the HSK syllabus (Center for Language Education and Cooperation, 2025)}
}
```

Replace `<SITE_URL>` with the dataset homepage.
