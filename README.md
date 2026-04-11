# aitee_training

応用情報技術者試験（AP）の学習を、**LLM訓練パイプラインのメタファに基づいて設計する**実験プロジェクト。

## 何をやろうとしているか

世間の試験対策（過去問周回、一問一答、暗記カード）を盲信せず、**脳科学・LLM的知見に基づいた学習システム**を組み立てる。受験者の認知リソースを「勉強法を考えること」ではなく「理解と想起そのもの」に全振りさせるための装置を作る、というのが目標。

中核アイデア: 受験者を1つのニューラルネットワークとみなし、LLM訓練の各フェーズ（Pre-training / SFT / Preference Optimization / RLVR）を学習設計に翻訳する。ただし人間脳の特性に応じた3つの補正を加える:

1. **フェーズはスペクトラム** — 離散切替ではなく mix ratio を連続制御する
2. **Engagement gating** — 入力だけでは勾配が流れない（「目が滑る」）。能動的処理を強制する仕掛けを全インプットに埋め込む
3. **Maintenance loop** — 人間の重みは drift する。LLMにはない「維持」フェーズを first-class で持つ必要がある

詳細な設計哲学は [CLAUDE.md](./CLAUDE.md) の「コンセプト」節を参照。

## レイヤ実装状況

| Layer | 状態 | 実装場所 |
|---|---|---|
| Layer 1: Pre-training | 初版完成 | `.claude/skills/pre-training/` + `.claude/skills/textbook-dispenser/` |
| Layer 2: SFT | 未着手 | (過去問データは `past_exam/` に既存) |
| Layer 3: Maintenance | 未着手 | — |

## 提供スキル

### `textbook-dispenser`

応用情報の教科書目次（全11章 / 81節 / 319 leaves）への純粋な読み取りレイヤ。曖昧な学習対象指定（leaf ID、節番号 `4-3-1`、タイトルの一部、章名など）を厳密な leaf 情報に解決する。状態を持たず、他のスキルから呼ばれる前提。

3つのモード:
- `resolve` — 曖昧入力を leaf / section / chapter に解決
- `lookup` — 厳密ID指定で詳細取得
- `neighbors` — 前後 leaf 取得（連続学習用）

教科書構造データ（`textbook_structure.json`）をスキル内部に内包しているので、外部依存なしに動く。

### `pre-training`

Layer 1（Pre-training）の本体。1 leaf を以下のエピソード構造で能動学習させる:

1. **Concept exposition** — 密度の高い説明
2. **Bridge** — 隣接概念への予告
3. **Engagement loop** — 10〜20問を1問ずつ、ジャンルを混ぜて出題（定義想起／対比／シナリオ適用／誤り発見）
4. **毎問フィードバック** — 正誤＋なぜ＋他選択肢の正体＋ニーモニック
5. **Episode summary** — 要点の圧縮
6. **Consent-gated transition** — 学習者の同意で次 leaf へ

なぜこの構造か: 補正2（engagement gating）の実装。受動的な読書では実効学習率がゼロに近づくため、説明→問題→フィードバックのループで forward pass を強制する。詳細は [SKILL.md](./.claude/skills/pre-training/SKILL.md) を参照。

参考実装は `ref/chat/chat.txt`（過去に同様の振る舞いをさせたAIとの会話ログ）。

## インストール

`dist/` に `.skill` 形式のパッケージ済みファイルを置いてあります:

```
dist/
├── textbook-dispenser.skill
└── pre-training.skill
```

Claude のスキルアップロード機能でインストール可能。**順序は textbook-dispenser を先にインストール**してください（pre-training が依存しているため）。

## 使い方の例

学習者が「デュアルシステムを勉強したい」と言った時の流れ:

1. pre-training スキルが起動
2. textbook-dispenser に「デュアルシステム」を投げる → `ch04_03_01「デュアルシステム構成」` に解決
3. 概念説明（定義・特徴・用途・隣接概念との違い）
4. 15問前後の問題を1問ずつ提示
5. 各問にフィードバック（正解の理由＋間違い選択肢の正体＋ニーモニック）
6. まとめ → 「次は ch04_03_02『デュプレックスシステム』に進みますか？」

## ディレクトリ構成

```
aitee_training/
├── CLAUDE.md                      # 設計哲学・マニフェスト・コンセプト
├── README.md                      # このファイル
├── ref/                           # 参考資料
│   ├── 目次.md                    # IPA シラバス Ver.7.2
│   ├── textbook.md                # 使用テキストの目次
│   ├── 法規制度ガイドライン.md
│   └── chat/chat.txt              # pre-training の参照実装
├── textbook/
│   └── textbook_structure.json    # 教科書目次の構造化データ
├── past_exam/                     # 過去問データ（Layer 2 用に温存）
├── .claude/skills/
│   ├── textbook-dispenser/        # 目次参照スキル
│   └── pre-training/              # Layer 1 学習スキル
└── dist/                          # 配布用 .skill パッケージ
```

## 開発の進め方

このプロジェクトはレイヤごとに段階実装する方針:

1. ✅ Layer 1（Pre-training）の最小実装 — テキスト1 leafを engagement loop で能動学習させる
2. Layer 2（SFT）の実装 — 過去問を試験フォーマット適応として扱う
3. Layer 3（Maintenance）の実装 — drift 防止と consolidation の並列ループ
4. 3層を統合制御するオーケストレータの実装
