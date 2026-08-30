---
name: skill-diagnoser
description: This skill should be used when analyzing test execution failures, identifying root causes across skill layers (spec, script, test_case), and formulating structured improvement plans.
license: Complete terms in LICENSE.txt
pattern: workflow
---

# Skill Diagnoser

## Overview

テストランナーが生成した評価レポート（`tests/results/latest_report.json` 等）、仕様書（`SKILL.md`）、および `scripts/` 配下の Python コードを多角的に分析し、最小限の安全な修正でテストを合格させるための根本原因を特定して改善方針（Improvement Plan）を策定する診断ワークフロー。

## Workflow Decision Tree

- **If** テスト結果レポートに失敗ケースが存在する場合 ➔ **Then** `scripts/diagnoser.py` で失敗コンテキスト（スタックトレース、入出力、関連コード）を抽出し、Step 2〜3 でエージェント自身が根本原因を分析して改善方針を決定する
- **If** すべてのテストが合格している場合 ➔ **Then** 追加の診断・改善をスキップし、上位 Tier 昇格または本番利用へ進む

## Step-by-Step Instructions

### Step 1: 決定論的失敗コンテキストの抽出 *(Tool: `scripts/diagnoser.py`)*

To extract structured failure context (failed test cases, error messages, stack traces, and relevant source code), run:
```bash
python scripts/diagnoser.py <skill_name> --format markdown
```

### Step 2: 根本原因の分析とレイヤー特定

出力されたコンテキストに基づき、エージェント自身が以下のどのレイヤーに原因があるかを推論・特定する：
1. **仕様層 (`spec`)**: トリガー説明文の不足、意思決定ツリーの分岐漏れ、指示文の不備（`SKILL.md`）
2. **ロジック層 (`script`)**: 引数パース不備、ゼロ除算、KeyError、エッジケース未対応（`scripts/*.py`）
3. **テストケース層 (`test_case`)**: テスト期待値側の仕様誤認、不正なアサーション（`tests/*.evalset.json`）
4. **知識・資料層 (`reference`)**: スキーマや利用規約の記載ミス（`references/*.md`）

### Step 3: 構造化改善計画（Improvement Plan）の策定

修正対象ファイル、具体的な差分方針、および安全な修正手順を策定する：
- **修正対象ファイル**: 相対パス（例: 対象スキルの実装コードや `SKILL.md`）
- **根本原因サマリー**: なぜ失敗したかの簡潔な技術的説明
- **推奨アクション**: どのようにコードまたは仕様を書き換えるべきかの具体的指示

## Usage Scenarios & Trigger Examples

- "pdf-tools スキルのテスト失敗原因を診断してください。"
- "最新のテストレポートから失敗箇所を特定して改善方針を出力して。"

## When NOT to Use This Skill

- **全テストが合格しており修復すべき問題がない場合**: 診断を実行する必要はない。
- **テストの実行やスコア測定そのものを行う場合**: 診断ではなく、`skill-evaluator` を使用する。
- **診断結果に基づきコード修正・再テスト・連鎖回帰テストまで一括実行する場合**: `skill-optimizer` を使用する。
- **新規スキルの設計・コード生成**: 診断ではなく、`skill-creator` を使用する。

## Bundled Resources

### `scripts/` (Executable Tools - Zero-LLM)
- **`scripts/diagnoser.py`**: テスト結果とアセットを決定論的に解析し構造化コンテキストを抽出する CLI ツール

## Guidelines & Best Practices

- 原因の特定は、テスト期待値の誤りなのか、実装コードのバグなのか、SKILL.mdの説明不足なのかを厳密に区別すること。
- 不要な大規模書き換えを避け、必要最小限かつ安全な修正計画を提示すること。
