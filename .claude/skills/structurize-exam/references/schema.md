# 構造化データスキーマ

## 1ファイル単位: `{exam_id}_am.json`

```json
{
  "exam_id": "2025r07h",
  "exam_name": "令和7年度春期",
  "type": "am",
  "questions": [
    {
      "number": 1,
      "body": "論理式P,Qがいずれも真であるとき、論理式Rの真偽にかかわらず真になる式はどれか。ここで、\"¬\"は否定を、\"∨\"は論理和を、\"∧\"は論理積を、\"→\"は含意（\"真→偽\"となるときに限り偽となる演算）を表す。",
      "choices": {
        "ア": "((P→Q)∧(Q→P))→(R→Q)",
        "イ": "((P→Q)∧(Q→P))→(Q→R)",
        "ウ": "((¬P)∨Q)∧(R→Q)",
        "エ": "(P→Q)→R"
      },
      "answer": "ア",
      "tags": ["ch01_01"],
      "has_figure": false,
      "figure_description": null
    },
    {
      "number": 6,
      "body": "図の2分探索木に1と0の二つの要素を順に追加したAVL木として、適切なものはどれか。",
      "choices": {
        "ア": "[図: AVL木パターンA]",
        "イ": "[図: AVL木パターンB]",
        "ウ": "[図: AVL木パターンC]",
        "エ": "[図: AVL木パターンD]"
      },
      "answer": "ウ",
      "tags": ["ch02_03"],
      "has_figure": true,
      "figure_description": "問題文に2分探索木の図あり。選択肢もそれぞれAVL木の図。OCRでは正確に読み取れない。"
    }
  ]
}
```

## フィールド定義

### トップレベル

| フィールド | 型 | 説明 |
|---|---|---|
| `exam_id` | string | 試験ID。OCRファイル名から導出。例: `"2025r07h"`, `"2011h23tokubetsu"` |
| `exam_name` | string | 試験の正式名称。OCRテキスト1ページ目から抽出。例: `"令和7年度春期"` |
| `type` | string | 常に `"am"`（午前問題） |
| `questions` | array | 問題オブジェクトの配列（通常80件） |

### questions[] の各要素

| フィールド | 型 | 説明 |
|---|---|---|
| `number` | integer | 問題番号（1〜80） |
| `body` | string | 問題文。選択肢は含めない。OCRの誤読を可能な限り修正した状態で格納する |
| `choices` | object | `{"ア": "...", "イ": "...", "ウ": "...", "エ": "..."}` の4択。図が含まれる選択肢は `"[図: 簡潔な説明]"` とする |
| `answer` | string | 正解の選択肢記号。`"ア"` / `"イ"` / `"ウ"` / `"エ"` のいずれか |
| `tags` | array of string | `ref/textbook_structure.json` の section id。複数可。詳細は tags.md を参照 |
| `has_figure` | boolean | 問題文または選択肢に図・表・グラフ等の視覚的要素が含まれるか |
| `figure_description` | string or null | `has_figure` が true の場合、図の概要説明。false なら `null` |

### body フィールドの品質基準

OCRテキストはそのまま使うのではなく、以下の修正を行う:

1. **明らかなOCR誤読の修正**: `"V/"` → `"∨"`、`"△"` → `"∧"`、`"×"` → `"x"` など、文脈から明らかに判断できる記号の修正
2. **改行・空白の正規化**: 意味のない改行を除去し、読みやすい形に整形
3. **修正不能な箇所はそのまま残す**: 推測が必要な箇所は無理に修正しない

### choices フィールドの注意点

- 選択肢が図のみの場合: `"[図: 回路図]"` のように記述し、`has_figure: true` にする
- 選択肢が数式の場合: できる限りテキスト表現に変換する
- 選択肢が表の場合: テキストで再現可能なら再現、不可能なら `"[図: 表の説明]"` とする

## 2. 全結合ファイル: `all_am.json`

```json
{
  "generated_at": "2026-03-01T12:00:00+09:00",
  "total_exams": 33,
  "total_questions": 2640,
  "stats": {
    "has_figure_count": 650,
    "has_figure_rate": 0.246,
    "tagged_count": 2500,
    "tagged_rate": 0.947
  },
  "exams": [
    { "...": "1ファイル単位の内容がそのまま入る" }
  ]
}
```

## 3. exam_id の命名規則

OCRファイル名 `{exam_id}_ap_am_qs.txt` から `exam_id` 部分を抽出する。

| ファイル名 | exam_id | exam_name |
|---|---|---|
| `2025r07h_ap_am_qs.txt` | `2025r07h` | 令和7年度春期 |
| `2025r07a_ap_am_qs.txt` | `2025r07a` | 令和7年度秋期 |
| `2011h23tokubetsu_ap_am_qs.txt` | `2011h23tokubetsu` | 平成23年度特別 |
| `2020r02o_ap_am_qs.txt` | `2020r02o` | 令和2年度10月 |

末尾の `h` = 春期、`a` = 秋期、`tokubetsu` = 特別、`o` = 10月（コロナ延期）。
