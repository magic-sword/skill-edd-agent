---
name: case-converter
description: This skill should be used when users need to convert text or identifier case styles (camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE, Title Case) across strings or files.
license: MIT
pattern: task_based
---

# Case Converter

## Overview

文字列およびテキストファイル内の識別子ケース形式（camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE, Title Case, lower, upper）を決定論的に相互変換します。

## Quick Start

文字列のケース変換を行うには、`scripts/case_converter.py` を実行する：

```bash
python scripts/case_converter.py "hello_world_example" --to camel
# Output: helloWorldExample
```

## Available Tasks

### Task 1: 構文・入力テキストの確認
変換対象の文字列またはファイルパス、および目的のケース形式（`camel`, `snake`, `pascal`, `kebab`, `constant`, `title`, `upper`, `lower`）を特定します。

### Task 2: ケース変換の実行 *(Tool: `scripts/case_converter.py`)*
`scripts/case_converter.py` を呼び出して変換を実行します。

```bash
# 文字列引数での変換
python scripts/case_converter.py <text> --to <target_case>

# ファイル入力・出力
python scripts/case_converter.py --file input.txt --to snake --output output.txt
```

### Task 3: 変換結果の検証
出力結果が期待通りのケース形式に変換されていることを確認し、ユーザーに返答します。

## Usage Scenarios & Trigger Examples

以下のようなリクエストを処理する際にトリガーされます：
- "この snake_case の変数リストを camelCase に変換して"
- "ファイル内の識別子を kebab-case に変換してほしい"
- "Convert 'foo_bar_baz' to PascalCase"

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):
- **粒度境界 (Granularity)**: 単純な `tr '[:lower:]' '[:upper:]'` や大文字・小文字変換のみのワンライナーで完結するタスク。
- **技術的限界 (Out-of-Scope)**: AST（抽象構文木）レベルでの高度なコードリファクタリング（言語固有の Language Server や AST ツールを利用すべき場合）。
- **ライフサイクル分離 (Lifecycle)**: スキル自体のテスト実行、診断、自己修復、Tier昇格（`skill-evolver` を使用すること）。
- **インベントリ照合 (Inventory)**: スキル雛形生成やパッケージ化作業（`skill-creator` を使用すること）。

## Requirements & Prerequisites

本スキルは Zero-dependency ツールとして設計されており、外部パッケージの追加インストールは不要です：
- **Python**: >= 3.10 (Python 標準ライブラリのみで動作)

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/case_converter.py`**: camelCase, snake_case, PascalCase, kebab-case 等の相互変換を行う Zero-dependency CLI ツール。

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 対応ケース形式一覧およびエッジケース仕様。

## Guidelines & Best Practices
- スクリプトは `--help` をサポートし、Python 標準ライブラリのみで動作します。
- 変換仕様の詳細については `references/guide.md` を参照する。

