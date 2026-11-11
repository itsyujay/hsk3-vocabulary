# SOURCES.md — inputs, licenses and redistribution status

Dataset target license: **CC BY 4.0**. A source is listed "OK" only if the
material we take from it can be redistributed inside a CC BY 4.0 dataset
without share-alike or non-commercial restrictions. Exact license texts are
cited per source. Project rule: definitions and example sentences are
written fresh; nothing is copied from share-alike or non-commercial sources.

| Source | What we use | License (exact file) | URL | OK under CC BY 4.0? |
|---|---|---|---|---|
| 《中文水平考试 HSK 考试大纲》 2025 syllabus + chinesetest.cn glossary query API | The 11,000-word list: hanzi (incl. sense numbering), official pinyin, POS (词性), levels + extra-level senses, appendix of 231 proper nouns. Fields we add ourselves: everything else. | Chinese government-affiliated publication (CLEC); no explicit copyright statement on the release. Used as facts: the word list, its levels, its pinyin and POS are factual reference data, not creative expression. | PDF: https://cdn.hskexam.net/resourceFiles/%E6%96%B0%E7%89%88HSK%E8%80%83%E8%AF%95%E5%A4%A7%E7%BA%B21219.pdf (sha256 ec74ce04…); API: https://www.chinesetest.cn (glossary query API) | **yes, with caveat** — we redistribute facts (word/level/pinyin/POS) from an official public syllabus; the PDF itself is not redistributed in the repo; no creative text is copied from it |
| GF 0025-2021 《国际中文教育中文水平等级标准》 | Secondary mapping `gf2021_level` and the GF2021-vs-2025 change summary | Chinese national (MOE) standard; no explicit copyright statement. Same reasoning: factual level assignments. | http://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/W020210329527301787356.pdf (fetched via Wayback 20210331121129; sha256 e451fdf0…) | **yes, with caveat** — facts only (level mapping); the scanned standard PDF is not redistributed |
| ivankra/hsk30 | GF 0025-2021 word list cross-check: `Pinyin`, `Level` columns of hsk30.csv (fed into data/review.csv as `gf2021_pinyin`) | MIT — https://github.com/ivankra/hsk30/blob/master/LICENSE | https://github.com/ivankra/hsk30 | **yes** (MIT; attribution: © 2023 Ivan Krasilnikov) |
| ofou/hsk | 2025 API mirror cross-check (词汇.csv); official 认读字 list 汉字.csv (3,088) and 手写字 list 手写汉字.csv (1,200) used verbatim as `char_level` / `writing_level` | MIT — https://github.com/ofou/hsk/blob/master/LICENSE | https://github.com/ofou/hsk | **yes** (MIT; © 2021 Shawky) |
| elkmovie/hsk30 | Not used (not cloned; ivankra/hsk30 covers the same GF 0025-2021 list) | MIT — https://github.com/elkmovie/hsk30/blob/main/LICENSE | https://github.com/elkmovie/hsk30 | n/a (not used) |
| drkameleon/complete-hsk-vocabulary | HSK 2.0 (2012) 'old' inclusive word lists — simplified headword + level only, used as secondary HSK2.0 cross-check | MIT for the repo — https://github.com/drkameleon/complete-hsk-vocabulary/blob/main/LICENSE — **but its English meanings come from CC-CEDICT (CC BY-SA 4.0)** | https://github.com/drkameleon/complete-hsk-vocabulary | **yes** — we take only the word/level facts; its meanings are never copied (share-alike) |
| clem109/hsk-vocabulary | Primary HSK 2.0 (2012) cumulative lists (hanzi + level only; `hsk2_level`, change computation). Its README sources it from gigacool/hanyu-shuiping-kaoshi; translations in that source are CC-CEDICT-derived, so we copy hanzi+level only. | MIT — https://github.com/clem109/hsk-vocabulary/blob/master/LICENSE | https://github.com/clem109/hsk-vocabulary | **yes** (MIT; © 2018 Clement Venard; no translation text reused) |
| pypinyin (python-pinyin, 0.55.0) | Programmatic readings for the pinyin review (data/review.csv) and the syllable inventory used to align official pinyin to hanzi. No pypinyin data files are redistributed. | MIT — https://github.com/mozillazg/python-pinyin/blob/master/LICENSE.txt (code and bundled data as distributed) | https://github.com/mozillazg/python-pinyin | **yes** — pinyin readings are facts; output of an MIT tool, not redistributed as data |
| OpenCC via opencc-python-reimplemented | Simplified→Traditional conversion for the `traditional` field. Mode **s2t** chosen over **s2twp**: s2t does character conversion only; s2twp also substitutes Taiwan vocabulary (信息→資訊, 软件→軟體), which would alter the syllabus headwords. | Apache-2.0 — https://github.com/BYVoid/OpenCC/blob/master/LICENSE (dictionary data same license); reimplemented Python binding: Apache-2.0 (sdist LICENSE) | https://github.com/leoxiaofei/opencc-python-reimplemented | **yes** (Apache-2.0, no share-alike) |
| Unihan database (Unicode CLDR UCD, latest) | `radical` (kRSUnicode radical number) and `stroke_count` (kTotalStrokes) in hsk3_chars.json. Downloaded to raw/unihan/Unihan.zip (not committed). | Unicode License v3 — https://www.unicode.org/license.txt | https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip | **yes** (permissive; © Unicode, Inc.) |
| cjkvi-ids | **Not used.** README "Licenses" section: ids.txt derives from CHISE IDS and "All other data are distributed under GPLv2" | GPLv2 — https://github.com/cjkvi/cjkvi-ids/blob/master/README.md | https://github.com/cjkvi/cjkvi-ids | **no** — share-alike; `ids`, `components`, `semantic_component`, `phonetic_component` stay null in hsk3_chars.json |
| SUBTLEX-CH (Cai & Brysbaert 2010) | **Not merged.** Ghent page and the article state the dataset is "freely available for research purposes" under a non-commercial grant; the article text is CC BY but the dataset grant is research-only | Unclear — https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch and https://doi.org/10.1371/journal.pone.0010729 | https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexch | **unclear / no** — research-only grant; `freq_rank` and `char_freq_rank` stay null |
| CC-CEDICT (MDBG) | **Not used.** Share-alike CC BY-SA 4.0 would force the whole dataset to be CC BY-SA | CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/ ; statement at https://www.mdbg.net/chinese | https://www.mdbg.net/chinese/dictionary?page=cedict | **no** — share-alike incompatible with CC BY 4.0 target |
| Make Me a Hanzi | **Not used** | GPL / Arphic-derived — https://github.com/skishore/makemeahanzi | https://github.com/skishore/makemeahanzi | **no** — not redistributable into CC BY 4.0 |
| Official pinyin disagreements (tone sandhi display, alternative readings) | Recorded only as review rows (data/review.csv); the official pinyin in the dataset is never altered | n/a (derived from the sources above) | — | n/a |

## Notes

- The 2025 syllabus PDF (raw/official/HSK-syllabus-2025-1219.pdf) and the GF
  0025-2021 scan (raw/official/GF0025-2021.pdf) are kept out of git
  (.gitignore) and are not part of any release artifact.
- English definitions, example sentences and cloze variants are written
  fresh for this project (no copying from Pleco, HelloChinese, textbooks,
  CC-CEDICT or other restricted sources).
- Update this table whenever a new input is added; record permissive-license
  confirmation before merging any new data.
