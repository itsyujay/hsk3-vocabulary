# SCHEMA.md — hsk3 dataset fields

Version of this document: matches `schema_version` in `manifest.json` (1.0.0).

The website repo consumes the release files in `dist/`. Every file listed in
`dist/manifest.json` is stable JSON/CSV with the fields documented here.
Breaking changes to any field bump the manifest's `schema_version` major.

## hsk3_words.json / hsk3_words.csv

Array of 11,000 records, one per syllabus entry. `id` is the stable key.
In the CSV, list fields are joined with `|` (nested lists with `,`),
booleans as `true`/`false`, null as empty.

| field | type | nullable | meaning |
|---|---|---|---|
| id | string | no | Stable id `hsk3-NNNNN`, from the official 序号 |
| no | integer | no | Official 序号 (1..11000) |
| hanzi | string | no | Simplified headword, sense digits stripped |
| hanzi_official | string | no | Raw official string, including sense digits (`点1`) |
| sense | integer | yes | Official sense number when the syllabus lists the word twice (`点1` → 1, `点2` → 2); null otherwise |
| variants | string[] | no | Split-off variant/slash/parenthesis forms; empty in the 2025 API (kept for schema stability) |
| traditional | string | no | Traditional form via OpenCC s2t (character conversion only; see SOURCES.md) |
| pinyin | string | no | Official pinyin with tone marks, official spacing/hyphens/apostrophes preserved; `/` separates official alternative readings |
| pinyin_numbered | string | no | Derived from `pinyin`: tone marks → digits, neutral = 5, ü → v (pypinyin TONE3 convention), erhua suffix `-r` unnumbered; separators preserved |
| level | int or "7-9" | no | Official base band: 1..6 or "7-9" |
| extra_levels | list | no | Additional bands parsed from `一级（四级）`-style levelNames (base level 1 with another sense/POS at level 4 → [4]) |
| pos | string | yes | Official 词性 (cixing) raw; null when the API omits it (496 entries) |
| pos_en | string[] | no | English POS codes for the non-parenthesized POS |
| pos_extra_en | string[][] | no | English POS codes per parenthesized group, parallel to `extra_levels` |
| en | string | yes | English definition; null until content build |
| example_zh | string | yes | Example sentence (Chinese); null until content build |
| example_pinyin | string | yes | Pinyin of the example; null until content build |
| example_en | string | yes | English of the example; null until content build |
| example_cloze | string | yes | Cloze variant of the example; null until content build |
| hsk2_level | integer | yes | Band in the 2012 HSK 2.0 list (1..6); null if new in HSK 3.0 |
| gf2021_level | int or "7-9" | yes | Band in GF 0025-2021; null if not in that list |
| change | string | no | vs HSK 2.0: `new` / `same` / `level_up` / `level_down` (removed HSK2 words appear only in hsk2_to_hsk3_changes.json) |
| audio_word | string | yes | Audio asset key for the headword; null (audio not built) |
| audio_example | string | yes | Audio asset key for the example; null |
| audio_word_voice_b | string | yes | Secondary-voice asset key; null |
| source | string | no | Provenance tag, always `hsk-syllabus-2025` |
| freq_rank | integer | yes | Corpus frequency rank; null (no license-clean source: SUBTLEX-CH is research-only) |
| topic_tags | string[] | no | Topic tags; empty until content build |
| register | string | yes | Register/usage note; null until content build |
| tone_pattern | string | no | Underlying dictionary tones per syllable joined with `-`, 5 = neutral; 一 = 1 and 不 = 4 even where the official string writes the sandhi surface tone; erhua base syllable keeps its own tone |
| tone_sandhi_surface | string | no | Rule-derived spoken tones: 3rd-tone sandhi (3→2 before 3, left-to-right), 一 before tone 4 → 2 / before 1,2,3 → 4, 不 before tone 4 → 2 |
| has_neutral_tone | boolean | no | True if any syllable is toneless in the official pinyin |
| has_erhua | boolean | no | True if the official pinyin attaches an erhua suffix `-r` |
| chars | string[] | no | Distinct characters of `hanzi`, in order |
| confusables | string[] | no | Near-homophone/shape-similar ids; empty (not built; only license-clean data allowed) |
| review_flags | string[] | no | Codes of open review.csv rows for this entry (`pinyin_disagreement`, `neutral_tone`, `sandhi`, `polyphone`, `variant_pinyin`, `pinyin_other`, `hsk2_source_conflict`) |

## hsk3_chars.json

Array of 3,088 records, one per distinct character in the 11,000 words.
Key: `char`.

| field | type | nullable | meaning |
|---|---|---|---|
| char | string | no | The character |
| pinyin | string[] | no | Readings of the character as used inside HSK words, official spellings; erhua words contribute no reading for 儿 (no separate syllable) |
| char_level | string | no | Official 认读字 band (`一级`..`六级`, `七-九级`) |
| writing_level | string | yes | Official 手写字 band (`二级`..`七-九级`); null for recognition-only characters |
| ids | string[] | no | Word ids (`hsk3-NNNNN`) containing the character |
| components | string[] | yes | Ideographic description components; null (cjkvi-ids data is GPLv2, not redistributable) |
| radical | string | yes | Kangxi radical character (from Unihan kRSUnicode radical number) |
| stroke_count | integer | yes | Total stroke count (Unihan kTotalStrokes) |
| etymology_type | string | yes | Null (no license-clean etymology source selected) |
| semantic_component | string | yes | Null (same reason) |
| phonetic_component | string | yes | Null (same reason) |
| hint_en | string | yes | Null (filled by the content build) |
| char_freq_rank | integer | yes | Null (SUBTLEX-CH is research-only) |
| words | string[] | no | Headwords containing the character (first occurrence per word) |

## Other release files

- **hsk3_proper_nouns.json** — 231 appendix records: `no`, `hanzi`,
  `pinyin` (null: the API gives none for the appendix), `category`
  (official 词性 of the appendix, e.g. `称呼`), `band` (`初等`/`中等`/`高等`),
  `source`.
- **levels/hsk3_level_N.json|csv** — the words records of one band
  (same fields as hsk3_words).
- **hsk2_to_hsk3_changes.json** — `hsk2_source_counts`,
  `hsk2_source_conflicts`, `hsk2_to_hsk3_counts` + `hsk2_to_hsk3_records`
  (`new`/`removed`/`level_up`/`level_down`/`same` entry lists),
  `gf2021_to_2025_counts` + `gf2021_to_2025`.
- **review.csv** — columns `id, no, hanzi, level, official_pinyin,
  pypinyin, gf2021_pinyin, issue_type, note, suggested, status`
  (`issue_type`: polyphone / neutral_tone / erhua / sandhi / disagreement /
  variant / other; `status`: open / info). The official pinyin in the
  dataset is never changed by this file.
