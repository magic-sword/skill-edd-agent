---
name: skill-evolver
description: This skill should be used when users or agents need to evaluate, diagnose test failures, iteratively self-heal, run cascade regression tests, and promote skills through quality tiers (Tier 1~3).
license: MIT
pattern: workflow
---

# Skill Evolver

## Overview

Agent Skills の品質保証、多層評価テスト実行、失敗原因のコンテキスト診断、自律的自己修復（Self-Healing Loop）、依存スキルの連鎖回帰テスト（Cascade Testing）、および Tier 昇格判定を統合オーケストレーションする自己改善メタスキル。

## Workflow Decision Tree

スキルの状態と要求に応じて、以下の決定ロジックに従って進行する：

- **If** スキルの評価テストを実行する場合 ➔ **Then** Step 1 で `edd eval <skill-name>` を実行し、合格率を確認する
- **If** テスト失敗が検知された場合 ➔ **Then** Step 2 で `edd diagnose <skill-name>` を実行して失敗コンテキストを抽出し、`SKILL.md` または `scripts/` を修正して再テストする
- **If** スキル修正後の安全な昇格を行う場合 ➔ **Then** Step 3 で `edd optimize <skill-name> --tier <target-tier>` を実行して連鎖回帰テストと Tier 昇格を実施する

## Step-by-Step Instructions

### Step 1: 多層評価テストの実行 *(Tool: `edd eval`)*
対象スキルの契約テスト（I/O型検査）およびシミュレーション評価（Trigger / Golden）を実行します：

```bash
# 全テストの実行
edd eval <skill-name>

# 特定テスト（契約テストのみ）の実行
edd eval <skill-name> --type contract
```

### Step 2: 失敗原因の構造化診断と自己修復 *(Tool: `edd diagnose`)*
テストが失敗した場合、構造化失敗コンテキスト（エラー詳細、現在の SKILL.md、関連スクリプト）を抽出します：

```bash
edd diagnose <skill-name>
```

抽出された診断情報を分析し、以下のいずれかを実行してスキルを自己修復します：
1. **プロンプト/指示の修正**: `SKILL.md` の Frontmatter、トリガー条件、または手順を更新。
2. **スクリプトの修正**: `scripts/` 配下の Python スクリプトのロジックや引数パースを修正。
3. **リファレンスの追加**: ドメイン知識の不足がある場合は `references/` を拡充。
4. **使用例の追加・修正**: エージェント向けの実装例が不足している場合は `examples/` を拡充。

### Step 3: 連鎖回帰テストと Tier 昇格判定 *(Tool: `edd optimize`)*
修正完了後、依存関係グラフ（DAG）に基づく連鎖回帰テストを実行し、上位 Tier への昇格判定を行います：

```bash
# Tier 1 (Production) への昇格
edd optimize <skill-name> --tier 1

# Tier 2 (Verified) への昇格
edd optimize <skill-name> --tier 2
```

## Usage Scenarios & Trigger Examples

- "case-converter スキルの評価テストを実行して結果を確認して"
- "テストに失敗したスキルの原因を診断して、自動修復してほしい"
- "修正したスキルが他の依存スキルを破壊していないか連鎖回帰テストを実行し、Tier 1 に昇格させて"

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):
- **粒度境界 (Granularity)**: 単発のワンライナーコマンド（`pytest tests/test_simple.py` 等）の直接実行のみで完結する単純なテスト確認。
- **技術的限界 (Out-of-Scope)**: 対象ドメインの個別業務処理（ケース変換やファイル解析など）。該当するドメイン特化スキルを直接実行すること。
- **ライフサイクル分離 (Lifecycle)**: 新規スキルの雛形スキャフォールディング、初期プロンプト設計、テンプレート素材管理（`skill-creator` を使用すること）。
- **インベントリ照合 (Inventory)**: スキル管理・評価ではなく、Python パッケージ全体のビルド・デプロイ作業（標準の `pip` / `twine` ツールを使用すること）。

## Requirements & Prerequisites

本スキルは EDD エコシステム公式の自己進化メタスキルであり、以下の前提環境で動作します：
- **Python**: >= 3.11
- **Package**: `pip install -e edd-agent-tools` (または `pip install edd-agent-tools`)
- **CLI**: `edd` コマンドが環境パスに解決可能であること

## Bundled Resources

### `references/` (On-Demand Knowledge)
- **`references/eval_framework.md`**: 多層評価テスト（契約、トリガー、ゴールデン、ジャッジ）の評価基準と仕様。
- **`references/tier_promotion.md`**: Tier 1〜3 の昇格基準と防壁仕様。

## Guidelines & Best Practices
- テスト失敗時は推測で修正せず、必ず `edd diagnose` の出力を精読してピンポイントで修正すること。
- Tier 昇格時は連鎖回帰テスト（Cascade Testing）を省略せず、システム全体の健全性を担保すること。
- ドメイン固有のロジックを持たないメタスキルには不要な `scripts/` ラッパーを配置せず、`edd` 統合 CLI を直接利用すること。

