---
name: skill-evolver
description: |
  Evaluates, diagnoses test failures, iteratively self-heals, runs cascade regression tests, and promotes skills through quality tiers (Tier 1~3).
  Use when the user or agent needs to run multi-layer evaluations, tune trigger descriptions, diagnose errors, self-heal skills, or promote tiers.
  Do NOT use for creating brand-new skill boilerplates or managing Python package releases.
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: workflow
---

# Skill Evolver

## When to use
- スキルの多層評価テスト（契約テスト、トリガー判定、ツール軌跡、共存テスト）を実行したい時
- トリガー説明文（Frontmatter description）を自動チューニングして発火精度を向上させたい時
- テスト失敗の原因を構造化診断し、自律修復（Self-Healing Loop）を行いたい時
- スキル改修後に連鎖回帰テスト（Cascade Testing）を実行し、上位 Tier（1〜3）へ昇格させたい時

## When NOT to use
- 単発のワンライナーコマンド（`pytest tests/test_simple.py` 等）の直接実行で完結する単純な確認
- 対象ドメインの個別業務処理（ケース変換やファイル解析など）自体の実行
- 新規スキルの雛形スキャフォールディング、初期プロンプト設計、テンプレート管理（`skill-creator` を使用すること）
- Python パッケージ全体のビルド・リリース作業

## Workflow
1. 多層評価テストの実行: 対象スキルの契約テスト、トリガー判定、ツール軌跡、共存テストを実行する。
   ```bash
   edd eval <skill-name>
   # pass^k 持続的信頼性検証
   edd eval <skill-name> --type contract --pass-k 3
   ```
2. Frontmatter トリガー説明文の自動チューニング: 必要に応じてルーティング精度を最適化する。
   ```bash
   edd tune-desc <skill-name> --target-accuracy 0.9
   ```
3. 失敗原因の構造化診断と自己修復: テスト失敗時、構造化失敗コンテキストを抽出し、スキルを修復する。
   ```bash
   edd diagnose <skill-name>
   ```
4. 連鎖回帰テストと Tier 昇格判定: 依存関係グラフ（DAG）に基づく連鎖回帰テストを実行し、Tier 昇格判定を行う。
   ```bash
   # Tier 1 昇格
   edd optimize <skill-name> --tier 1
   # Tier 3 昇格 (Human Sign-off 必須)
   edd optimize <skill-name> --tier 3 --yes
   ```

## Examples
- Input: "Evaluate case-converter skill and verify all contract cases pass" → Output: "All contract tests and EDD composite cases passed (Accuracy: 1.0)"
- Input: "Diagnose test failures in secret-sanitizer and promote to Tier 2" → Output: "Diagnosed failure, repaired rubric, promoted to Tier 2"

## Output format
- テスト実行サマリー（合格数、失敗数、精度）、診断結果、および Tier 昇格結果ステータスを提示する。

## Anti-patterns to avoid
- テスト失敗時に原因を推測だけで修正せず、必ず `edd diagnose` の出力を精読してピンポイントで修正すること。
- Tier 昇格時に連鎖回帰テスト（Cascade Testing）を省略してシステム全体の整合性を壊さないこと。
- メタスキル内に不要な多層ラッパースクリプトを自作せず、統合 CLI `edd` を直接利用すること。

## Requirements & Prerequisites
本スキルは EDD エコシステム公式の自己進化メタスキルであり、以下の前提環境で動作します：
- **Python**: >= 3.11
- **Package**: `pip install -e edd-agent-tools` (または `pip install edd-agent-tools`)
- **CLI**: `edd` コマンドが環境パスに解決可能であること

## Bundled Resources
### `references/` (On-Demand Knowledge)
- **`references/eval_framework.md`**: 多層評価テスト（契約、トリガー、軌跡、ゴールデン、ジャッジ、共存）の評価基準と仕様。
- **`references/tier_promotion.md`**: Tier 1〜3 の昇格基準と Human Sign-off 仕様。
