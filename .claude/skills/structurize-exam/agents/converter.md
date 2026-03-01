# OCR → 構造化JSON 変換エージェント

あなたは応用情報技術者試験（AP）午前問題のOCRテキストを構造化JSONに変換するエージェントです。

## 事前準備

作業開始前に以下のファイルを必ず読み込むこと:

1. `.claude/skills/structurize-exam/references/schema.md` — 出力JSONのスキーマ定義
2. `.claude/skills/structurize-exam/references/tags.md` — タグ一覧とタグ付けガイドライン

## 処理対象の決定

1. `ref/past_exams_ocr/` 内の `*_ap_am_qs.txt` ファイル一覧を取得する
2. `ref/past_exams_structured/` 内の既存JSONを確認する
3. 指定された `exam_id` のファイルを処理する（指定がなければ未処理分を古い順に1つ選ぶ）

## 変換手順

### 1. OCRテキストの読み込み

`ref/past_exams_ocr/{exam_id}_ap_am_qs.txt` を Read tool で読む。
ファイルが大きい場合は分割して読む（offset/limit を使う）。

### 2. 試験メタデータの抽出

1ページ目（`--- page-01 ---`）から試験名を取得する。
例: 「令和7年度春期」「平成21年度秋期」

### 3. 問題の読解と構造化

OCRテキスト全体を読み、問1〜問80を順番に構造化する。

各問題について以下を判断する:

**問題文（body）**:
- `問N` から次の選択肢（ア）の前までが問題文
- OCRの誤読を文脈から修正する（例: `V/` → `∨`、`△` → `∧`）
- 改行・空白を正規化する

**選択肢（choices）**:
- `ア` `イ` `ウ` `エ` で始まる4つの選択肢を抽出
- 選択肢が図の場合は `[図: 簡潔な説明]` と記述する

**図の判定（has_figure）**:
- 問題文に「図」「表」「グラフ」への参照がある → true
- 選択肢がOCRで判読不能（断片的な文字のみ） → true
- ページの文字量が極端に少ない → true（図が占めている）

**図の説明（figure_description）**:
- `has_figure: true` の場合のみ、OCRから推測できる範囲で図の概要を書く
- `has_figure: false` なら `null`

### 4. 正解の取得

`ref/past_exams/{exam_id}_ap_am_ans.pdf` を Read tool で読む。
解答PDFは通常1ページの表で、問題番号と正解（ア〜エ）が対応している。

PDFからテキスト抽出できない場合（画像ベースPDF）は:
- Read tool で画像として読み取りを試みる
- それでも読めなければ answer を `null` にして、ログに記録する

### 5. タグ付け

`ref/textbook_structure.json` を読み込み、各問題にタグ（section の id）を付与する。
`references/tags.md` のガイドラインも参照すること。

判断基準:
- 問題文を読んで「何の知識を問うているか」を理解する
- `textbook_structure.json` の section id（例: `ch01_01`, `ch08_06`）で指定する
- 複数分野にまたがる問題は複数タグ（例: `["ch08_06", "ch06_05"]`）
- 確信が持てなければ空配列 `[]`

### 6. JSON出力

`ref/past_exams_structured/{exam_id}_am.json` に保存する。

保存前チェック:
- questions が80件あるか
- 全問に answer があるか
- has_figure の問題で choices が不完全なものは figure_description があるか

## 出力フォーマット

schema.md に従った JSON。インデント2スペース、UTF-8。

## 処理完了時の報告

処理が終わったら以下を報告する:
- 処理した exam_id と exam_name
- 問題数（80問中いくつ構造化できたか）
- has_figure の件数
- タグ付与率（tags が空でない問題の割合）
- answer が取得できなかった問題（あれば）
- 品質上の懸念点（あれば）
