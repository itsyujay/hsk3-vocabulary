# hsk3-vocabulary

All 11,000 words of the HSK 3.0 syllabus as JSON and CSV, with pinyin, English definitions and example sentences.

Browse the words, read them level by level and download the files at **https://hsk.yujay.dev**.

## Words per level

| Level | Words |
|---|---:|
| HSK 1 | 300 |
| HSK 2 | 200 |
| HSK 3 | 500 |
| HSK 4 | 1,000 |
| HSK 5 | 1,600 |
| HSK 6 | 1,800 |
| HSK 7–9 | 5,600 |
| **Total** | **11,000** |

Every word has an English definition and an example sentence.

Also included: 3,088 characters (`hsk3_chars.json`) and the 231 proper nouns from the syllabus appendix (`hsk3_proper_nouns.json`). Counts are for data version 2026.11.7, schema 2.0.0.

## Downloads

| File (in `dist/`) | Contents |
|---|---|
| `hsk3_words.json` / `hsk3_words.csv` | all 11,000 words |
| `levels/hsk3_level_{1..6,7-9}.json` / `.csv` | the words of one level |
| `hsk3_chars.json` | 3,088 characters |
| `hsk3_proper_nouns.json` | 231 proper nouns |
| `hsk2_to_hsk3_changes.json` | words added, removed or moved since HSK 2.0 |
| `review.csv` | pinyin points worth a second look |
| `manifest.json` | schema version, data version, record counts and sha256 of every file |

The same word lists are on the site: CSV and JSON for all words and for each level, and a printable PDF per level (hanzi, pinyin and English) at https://hsk.yujay.dev/hsk-pdf.

## Fields (schema 2.0.0)

### Words: `hsk3_words.json`, `hsk3_words.csv`, `levels/*`

One record per syllabus entry. In the CSV, lists are joined with `|`, booleans are `true`/`false` and null is empty.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable id `hsk3-NNNNN`, from the official number |
| `no` | integer | Official number, 1–11000 |
| `hanzi` | string | Simplified headword |
| `hanzi_official` | string | The official string, including sense digits (`点1`) |
| `sense` | integer or null | Sense number when the syllabus lists a word twice |
| `variants` | string[] | Variant forms |
| `traditional` | string | Traditional form (character conversion) |
| `pinyin` | string | Official pinyin with tone marks; `/` separates alternative readings |
| `pinyin_numbered` | string | Pinyin with tone numbers, neutral tone = 5, ü = v |
| `level` | integer or `"7-9"` | Official level: 1–6 or `"7-9"` |
| `extra_levels` | list | Further levels where another sense or part of speech is listed |
| `pos` | string or null | Official part of speech, in Chinese |
| `pos_en` | string[] | Part of speech in English |
| `pos_extra_en` | string[][] | Parts of speech for `extra_levels`, in the same order |
| `en` | string or null | English definition |
| `example_zh` | string or null | Example sentence |
| `example_pinyin` | string or null | Pinyin of the example |
| `example_en` | string or null | English translation of the example |
| `example_cloze` | string or null | The example with the headword replaced by ＿＿ |
| `hsk2_level` | integer or null | Level in the HSK 2.0 list (1–6); null if new |
| `gf2021_level` | integer, `"7-9"` or null | Level in GF 0025-2021; null if not listed there |
| `change` | string | Against HSK 2.0: `new`, `same`, `level_up` or `level_down` |
| `audio_word`, `audio_example`, `audio_word_voice_b` | string or null | Audio file paths |
| `source` | string | Always `hsk-syllabus-2025` |
| `freq_rank` | integer or null | Frequency rank |
| `topic_tags` | string[] | One to three topic tags |
| `register` | string or null | `spoken`, `neutral`, `written` or `internet` |
| `tone_pattern` | string | Dictionary tones per syllable, e.g. `3-3`; 5 = neutral |
| `tone_sandhi_surface` | string | Spoken tones after tone sandhi, e.g. `2-3` |
| `has_neutral_tone` | boolean | Any toneless syllable |
| `has_erhua` | boolean | Ends in an erhua `-r` |
| `chars` | string[] | Distinct characters of the headword, in order |
| `confusables` | string[] | Ids of easily confused words |
| `review_flags` | string[] | Open `review.csv` issues for this word |

In this release `audio_word`, `audio_example`, `audio_word_voice_b` and `freq_rank` are null, and `variants` and `confusables` are empty.

### Characters: `hsk3_chars.json`

| Field | Type | Meaning |
|---|---|---|
| `char` | string | The character |
| `pinyin` | string[] | Its readings inside HSK words |
| `char_level` | string | Official recognition level (`一级` … `七-九级`) |
| `writing_level` | string or null | Official handwriting level; null if recognition only |
| `ids` | string or null | Ideographic description sequence |
| `word_ids` | string[] | Ids of the words that contain the character |
| `components` | string[] or null | Components |
| `radical` | string or null | Kangxi radical |
| `stroke_count` | integer or null | Total strokes |
| `etymology_type` | string or null | Character formation type |
| `semantic_component`, `phonetic_component` | string or null | Meaning and sound components |
| `hint_en` | string or null | Short English memory hint |
| `char_freq_rank` | integer or null | Character frequency rank |
| `words` | string[] | Headwords that contain the character |

In this release `ids`, `components`, `etymology_type`, `semantic_component`, `phonetic_component`, `hint_en` and `char_freq_rank` are null.

The full field reference is in `dist/SCHEMA.md`.

## Usage

Python, all HSK 1 words with their examples:

```python
import json

words = json.load(open("hsk3_words.json", encoding="utf-8"))
for w in words:
    if w["level"] == 1:
        print(w["hanzi"], w["pinyin"], w["en"], w["example_zh"])
```

JavaScript, look up a word:

```js
import words from './hsk3_words.json' with { type: 'json' };

const byHanzi = new Map(words.map((w) => [w.hanzi, w]));
console.log(byHanzi.get('学习').en); // "to study; to learn"
```

Command line, the English of every HSK 7–9 word:

```sh
jq -r '.[] | select(.level == "7-9") | "\(.hanzi)\t\(.pinyin)\t\(.en)"' hsk3_words.json
```

Spreadsheets: open `hsk3_words.csv` or a level CSV as UTF-8.

## Source

The word list, official pinyin, parts of speech and levels come from the 《中文水平考试 HSK 考试大纲》 (HSK syllabus) published by the Center for Language Education and Cooperation (CLEC), released 2025-11, in force from 2026-07. English definitions, example sentences and derived fields belong to this dataset. `SOURCES.md` lists every source and its licence.

## License

- Data (every JSON and CSV file): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see `LICENSE`.
- Scripts: MIT, see `LICENSE-CODE`.
- Audio, distributed separately: covered by `LICENSE-AUDIO`.

## How to cite

> Yujay. *hsk3-vocabulary: HSK 3.0 vocabulary dataset*, data version 2026.11.7. 2026. https://hsk.yujay.dev. CC BY 4.0. Word list from the Center for Language Education and Cooperation, 《中文水平考试 HSK 考试大纲》, 2025.

```bibtex
@misc{hsk3vocabulary2026,
  author       = {Yujay},
  title        = {hsk3-vocabulary: {HSK} 3.0 vocabulary dataset},
  year         = {2026},
  howpublished = {\url{https://hsk.yujay.dev}},
  note         = {Data version 2026.11.7. CC BY 4.0. Word list from the HSK syllabus (Center for Language Education and Cooperation, 2025)}
}
```

HSK is a trademark of CLEC. This dataset is not affiliated with CLEC.
