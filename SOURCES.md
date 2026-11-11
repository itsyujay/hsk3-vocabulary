# Sources and licenses

## Data sources used

| Source | Used for | License | URL |
|---|---|---|---|
| 《中文水平考试 HSK 考试大纲》 (Center for Language Education and Cooperation, released 2025-11, in force 2026-07) and its official vocabulary query service | Word list (11,000 entries), levels, official pinyin, parts of speech, 231-entry proper-noun appendix, official character lists | Official public syllabus; word list, levels, pinyin and parts of speech are reproduced as factual data. The syllabus PDF itself is not redistributed. | https://www.chinesetest.cn/syllabus ; PDF: https://cdn.hskexam.net/resourceFiles/%E6%96%B0%E7%89%88HSK%E8%80%83%E8%AF%95%E5%A4%A7%E7%BA%B21219.pdf (sha256 ec74ce0439e837bbb15154be13e747ae798903b2fd3a331629df6c3b45504941) |
| GF 0025-2021 《国际中文教育中文水平等级标准》 (Ministry of Education of the PRC) | `gf2021_level` mapping | Official national standard; level assignments reproduced as factual data | http://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/t20210329_523304.html |
| ivankra/hsk30 | GF 0025-2021 word list and pinyin (cross-check, `gf2021_level`) | MIT | https://github.com/ivankra/hsk30 |
| ofou/hsk | Official character lists (认读字 / 手写字) for `char_level`, `writing_level`; cross-check of the 2025 word list | MIT | https://github.com/ofou/hsk |
| clem109/hsk-vocabulary | HSK 2.0 (2012) word levels (`hsk2_level`, `change`) - headwords and levels only | MIT | https://github.com/clem109/hsk-vocabulary |
| drkameleon/complete-hsk-vocabulary | HSK 2.0 (2012) word levels, cross-check - headwords and levels only | MIT | https://github.com/drkameleon/complete-hsk-vocabulary |
| Unihan database (Unicode) | `radical`, `stroke_count` | Unicode License v3 | https://www.unicode.org/license.txt |
| OpenCC | Traditional forms (`traditional`, s2t conversion) | Apache-2.0 | https://github.com/BYVoid/OpenCC |
| pypinyin | Pinyin cross-check for `review.csv` | MIT | https://github.com/mozillazg/python-pinyin |

English definitions, example sentences, example translations, cloze items,
topic tags and register labels are original to this dataset.

## Citation

If you use this dataset, please cite the official syllabus and this dataset:

- 中外语言交流合作中心. 《中文水平考试 HSK 考试大纲》. 2025.
- hsk3-vocabulary: HSK 3.0 vocabulary dataset, version as listed in `dist/manifest.json`.
