---
name: case-converter
description: |
  Converts text or identifier case styles (camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE, Title Case) across strings or files.
  Use when the user asks to convert naming conventions, format code identifiers, or transform variable cases.
  Do NOT use for trivial single-word uppercase/lowercase or complex AST-based code refactoring.
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: task_based
---

# Case Converter

## When to use
- snake_case や camelCase などの識別子・命名規則を別のケーススタイルに変換したい時
- ソースコードやテキストファイル内の一括ケース形式を整形・統一したい時
- "Convert 'foo_bar_baz' to PascalCase" などの命名変換要求を処理する時

## When NOT to use
- 単純な `tr '[:lower:]' '[:upper:]'` 等の1単語の大文字・小文字変換で完結するタスク
- AST（抽象構文木）レベルでの高度なプログラミング言語リファクタリング
- スキル自体のテスト実行、診断、自己修復、Tier昇格（`skill-evolver` を使用すること）
- スキル雛形生成やパッケージ化作業（`skill-creator` を使用すること）

## Workflow
1. 構文・入力テキストの確認: 変換対象の文字列またはファイルパス、および目的のケース形式（`camel`, `snake`, `pascal`, `kebab`, `constant`, `title`, `upper`, `lower`）を特定する。
2. ケース変換の実行: `scripts/case_converter.py` を呼び出して決定論的に変換を実行する。
   ```bash
   # 文字列引数での変換
   python scripts/case_converter.py <text> --to <target_case>

   # ファイル入力・出力
   python scripts/case_converter.py --file input.txt --to snake --output output.txt
   ```
3. 変換結果の検証: 出力結果が期待通りのケース形式に変換されていることを確認し、ユーザーに返答する。

## Examples
- Input: "Convert 'hello_world_example' to camelCase" → Output: "helloWorldExample"
- Input: "Convert 'UserProfileData' to kebab-case" → Output: "user-profile-data"
- Input: "Convert 'api_response_status' to CONSTANT_CASE" → Output: "API_RESPONSE_STATUS"

## Output format
- 単一識別子の変換時は余計な会話フィラーを挟まず、変換後の識別子を直接提示する。
- ファイル一括変換時は変更差分または出力先パスを明確に示す。

## Anti-patterns to avoid
- スクリプトの中身を無駄に読み込んでコンテキストを消費しないこと（`--help` で引数仕様を確認する）。
- ファイル一括変換時に入力パターンのサンプリングを行わずにいきなり上書き実行しないこと。
- 対象外の構文やコメントを不用意に破壊しないこと。

## Requirements & Prerequisites
本スキルは Zero-dependency ツールとして設計されており、外部パッケージの追加インストールは不要です：
- **Python**: >= 3.10 (Python 標準ライブラリのみで動作)

## Bundled Resources
### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/case_converter.py`**: camelCase, snake_case, PascalCase, kebab-case 等の相互変換を行う Zero-dependency CLI ツール。

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 対応ケース形式一覧およびエッジケース仕様。

### `examples/` (Usage Patterns)
- **`examples/case_conversion_examples.py`**: 各種ケース変換の具体的な引数・実行パターン集。

