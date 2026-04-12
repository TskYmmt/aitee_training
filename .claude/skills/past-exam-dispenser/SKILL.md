---
name: past-exam-dispenser
description: 応用情報技術者試験の過去問（2009〜2025年、全33回分 2640問）をセクションタグ・年度・キーワードで検索して取得するための読み取り専用ディスペンサー。SFTスキルが変形問題を生成する際の seed 取得に使う。過去問を参照する全ての作業の入口として使うこと。ある単元にどんな過去問が出ているか調べたい時、特定年度の問題を見たい時、過去問のキーワード検索をしたい時にも使う。
---

# past-exam-dispenser

応用情報技術者試験の過去問（2009〜2025年、午前問題 全33回 × 80問 = 2640問）への純粋な読み取りレイヤ。SFT スキルが過去問を seed として変形問題を生成する際のデータソース。

## なぜこのスキルが存在するか

Layer 2（SFT）では、過去問をそのまま解かせるのではなく、**過去問を seed にした変形問題を大量生成**する。そのためにまず「この leaf / section にはどんな過去問があるか」を効率的に取得する手段が必要。このディスペンサーがその役割を担う。

状態を持たない。進捗・スケジュール・学習履歴は管理しない。

## ディレクトリ構成

```
past-exam-dispenser/
├── SKILL.md
├── data/
│   ├── 2009h21a_am.json
│   ├── ...
│   └── 2025r07h_am.json   # 全33ファイルを内包
└── scripts/
    └── dispense.py
```

## 使い方

4つのモードを Bash 経由で呼び出す。出力は常に JSON。

```bash
# セクションタグで検索（SFT の主要パス）
python3 scripts/dispense.py by-section ch04_03

# 選択肢込みの完全データが必要な場合
python3 scripts/dispense.py by-section ch04_03 --full

# 年度指定
python3 scripts/dispense.py by-exam 2025r07h

# キーワード検索
python3 scripts/dispense.py search "デュアルシステム"

# 統計情報
python3 scripts/dispense.py stats
```

呼び出し時のパス:
```bash
python3 /Users/tskymmt/git/aitee_training/.claude/skills/past-exam-dispenser/scripts/dispense.py by-section ch04_03 --full
```

## モード別の挙動

### `by-section` — SFT の主要パス

セクションタグに一致する全問題を返す。**過去問のタグはセクションレベル**（ch04_03 であって ch04_03_01 ではない）なので、1セクション内の全 leaf の問題がまとめて返る。

SFT スキルが「leaf ch04_03_01 の変形問題を作りたい」と思ったら:
1. leaf ID `ch04_03_01` から section `ch04_03` を抽出（末尾の `_01` を除去）
2. `by-section ch04_03 --full` を呼ぶ
3. 返ってきた問題群を seed にして、対象 leaf に関連するものを選び変形問題を生成

### `by-exam` — 年度指定

特定年度の全80問を返す。模試的な使い方や、年度間の傾向比較に使う。

### `search` — キーワード検索

問題文（body）に対する部分一致検索。最大30件を返す。概念横断的に「この用語がどう問われてきたか」を探るのに使う。

### `stats` — 統計情報

全体の問題数、セクション別・年度別の分布を返す。カリキュラム設計やカバレッジ確認に使う。

## 出力フォーマット

### `--full` なし（デフォルト: summary モード）

```json
{
  "exam_id": "2025r07h",
  "exam_name": "令和7年度春期",
  "number": 1,
  "body": "論理式P,Qがいずれも真であるとき...(120文字で切り詰め)",
  "answer": "エ",
  "tags": ["ch01_01"],
  "has_figure": false
}
```

body は120文字で切り詰め。問題の概要確認用。

### `--full` あり

```json
{
  "exam_id": "2025r07h",
  "exam_name": "令和7年度春期",
  "number": 1,
  "body": "（全文）",
  "choices": {"ア": "...", "イ": "...", "ウ": "...", "エ": "..."},
  "answer": "エ",
  "tags": ["ch01_01"],
  "has_figure": false,
  "figure_description": null
}
```

SFT スキルが seed にする場合は `--full` を使うこと。choices が無いと変形問題の distractor を作る参考にならない。

## タグ体系について

過去問のタグは **セクションレベル**（`ch04_03`）で付与されている。leaf レベル（`ch04_03_01`）ではない。

セクション → leaf のマッピングは textbook-dispenser が持っている。SFT スキルは textbook-dispenser で leaf を確定し、その section ID を抽出してから、past-exam-dispenser を呼ぶ、という流れになる。

## データカバレッジ

- 33回分（2009春〜2025春）
- 全2640問
- 81セクション全てにタグ付け済み
- セクションあたり 1〜159問（中央値19、平均33）
- 図付き問題あり（has_figure で識別可）

## このスキルが扱わないこと

- 問題の生成・変形（SFT スキルの責務）
- 学習進捗の追跡
- 正答率の記録
- leaf レベルへの問題振り分け（SFT スキルが runtime で判断する）
