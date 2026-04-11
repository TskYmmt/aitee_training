---
name: textbook-dispenser
description: 応用情報技術者試験のテキスト目次構造（textbook_structure.json）から、特定のleaf（サブセクション）の情報、隣接leaf、章/節の構造を引き出すための読み取り専用ディスペンサー。学習対象を曖昧に指定された場合（leaf ID、節番号「4-3-1」、タイトルの一部、章名など）に厳密なleaf情報へ解決する。pre-trainingスキルや他の学習スキルがテキストの構造を参照する必要がある時には必ずこのスキルを使うこと。応用情報の章立て、サブセクション一覧、特定トピックがテキストのどこにあるか、ある単元の前後にどの単元があるかを知りたい場合にも使う。テキストを参照する全ての作業の入口として使うこと。
---

# textbook-dispenser

応用情報技術者試験テキスト（全11章 / 81節 / 319 leaves）の目次構造への純粋な読み取りレイヤ。学習者の曖昧な「これを勉強したい」を、厳密な leaf ID と隣接情報に解決する。

## なぜこのスキルが存在するか

学習者は普通「ch04_03_01 を学習したい」とは言わない。「デュアルシステム」「4章の3節」「信頼性設計のところ」のような曖昧な指示を出す。一方、学習システム（pre-training スキルなど）は内部的に厳密な leaf ID で動作する必要がある。このギャップを埋めるのが dispenser の役割。

dispenser は**状態を持たない**: 進捗・既習・スケジュールなどは管理しない。純粋に「目次構造を引く」だけ。

## ディレクトリ構成

```
textbook-dispenser/
├── SKILL.md
├── data/
│   └── textbook_structure.json   # 内包データ（外部依存ゼロ）
└── scripts/
    └── dispense.py               # CLIエントリ
```

## 使い方の基本

3つのモードを Bash 経由で呼び出す。出力は常に JSON。

```bash
# 主要モード: 曖昧入力を解決
python3 scripts/dispense.py resolve "<query>"

# 厳密ID指定での詳細取得
python3 scripts/dispense.py lookup <leaf_id>

# 前後の leaf 取得
python3 scripts/dispense.py neighbors <leaf_id>
```

呼び出し時はカレントディレクトリをスキルルートにすると相対パスが整う:

```bash
cd .claude/skills/textbook-dispenser && python3 scripts/dispense.py resolve "デュアルシステム"
```

または絶対パスで:
```bash
python3 .claude/skills/textbook-dispenser/scripts/dispense.py resolve "デュアルシステム"
```

## モード別の挙動

### `resolve` — 主要モード

学習者の曖昧な入力を、厳密な leaf 情報か候補リストに解決する。**最初に呼ぶべきはこのモード**。

解決の優先順位:
1. 厳密 ID 一致（`ch04_03_01`、`ch04_03`、`ch04`）
2. 節番号の正規化（`4-3-1` → `ch04_03_01`、`4-3` → `ch04_03`、`4` → `ch04`）
3. leaf タイトルの検索（完全一致 > 前方一致 > 部分一致）
4. section タイトルの検索
5. chapter タイトルの検索

#### 入力例と返却

| 入力 | 解決される対象 | status |
|---|---|---|
| `ch04_03_01` | 単一leaf | `ok` |
| `デュアルシステム` | 単一leaf（部分一致） | `ok` |
| `4-3-1` | 単一leaf（正規化） | `ok` |
| `4-3` | section配下のleaf一覧 | `ambiguous` |
| `信頼性` | 複数leaf候補 | `ambiguous` |
| `4` | chapter配下のsection一覧 | `ambiguous` |
| `存在しない` | 該当なし | `not_found` |

### `lookup` — 厳密ID指定

leaf ID が既に確定している時に使う。`resolve` で曖昧解消が済んだ後の詳細取得や、隣接 leaf も含めた完全な情報が必要な時。

```bash
python3 scripts/dispense.py lookup ch04_03_01
```

### `neighbors` — 前後取得

連続学習で次の leaf に進みたい時、または前後の文脈を確認したい時。

```bash
python3 scripts/dispense.py neighbors ch04_03_01
```

`prev` / `current` / `next` の3つを返す。最初の leaf では `prev=null`、最後の leaf では `next=null`。

## 出力の status を必ず最初に確認すること

出力 JSON の `status` フィールドを確認してから処理を分岐する。値は5種類:

- `ok`: 単一の結果が解決された。`result` フィールドに leaf 情報がある
- `ambiguous`: 複数候補がある。`candidates` フィールドにリストがある。ユーザーに提示して選んでもらう
- `too_many`: マッチが10件超。`preview` を見せて、より具体的な検索を促す
- `not_found`: 該当なし。`hint` を読んでユーザーに別の検索方法を提案する

例:
```python
result = json.loads(output)
if result["status"] == "ok":
    leaf = result["result"]
    # leaf を使って学習を進める
elif result["status"] == "ambiguous":
    candidates = result["candidates"]
    # ユーザーに番号付きリストで提示し、選んでもらう
elif result["status"] == "too_many":
    # より絞り込んだ検索を促す
elif result["status"] == "not_found":
    # hint をユーザーに伝える
```

## column の扱い

`textbook_structure.json` には 58 個の「コラム記事」（`column: true`）が含まれる。これらも通常の leaf として扱われ、`is_column: true` フラグで区別されるだけ。

学習フローに含めるかどうかは呼び出し側（pre-training スキルなど）の判断に委ねる。dispenser は区別なく返す。

## leaf 情報の構造

`status: ok` で返される `result` フィールドは以下の構造:

```json
{
  "id": "ch04_03_01",
  "title": "デュアルシステム構成",
  "is_column": false,
  "chapter": { "id": "ch04", "title": "システム構成要素" },
  "section": { "id": "ch04_03", "title": "システムの構成と信頼性設計" },
  "linear_index": 88,
  "prev": { "id": "...", "title": "...", "chapter": "...", "section": "...", "is_column": false },
  "next": { "id": "...", "title": "...", "chapter": "...", "section": "...", "is_column": false }
}
```

`linear_index` は全 319 leaves を線形化した時の位置（0始まり）。

## 候補リストの構造

`status: ambiguous` で返される `candidates` の各エントリ:

```json
{
  "id": "ch04_03_01",
  "title": "デュアルシステム構成",
  "type": "leaf",            // "leaf" | "section" | "chapter"
  "is_column": false,        // type==leaf の時のみ
  "full_path": "システム構成要素 > システムの構成と信頼性設計 > デュアルシステム構成"
}
```

`full_path` をユーザーに見せると、どの位置の何かが一目で分かる。

## このスキルが扱わないこと

dispenser は読み取り専用かつ状態なし。以下は他のスキルや上位レイヤの責任:

- 学習進捗の追跡（どの leaf を完了したか）
- スケジューリング（次に何を復習すべきか）
- 学習コンテンツの生成（説明、問題、フィードバック）
- ユーザーごとの履歴管理

これらが必要なら、別のスキルが dispenser を呼び出して情報を得た上で、自前で状態を持つ。
