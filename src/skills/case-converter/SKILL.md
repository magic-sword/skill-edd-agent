---
name: case-converter
description: This skill should be used when a user needs to convert text strings into different case formats such as uppercase, lowercase, camelCase, or snake_case. It provides a utility for standard text manipulation tasks.
license: Complete terms in LICENSE.txt
pattern: task_based
---

# Case Converter

## Overview

このスキルは、入力された文字列を大文字、小文字、キャメルケース、スネークケースなど、指定された形式に変換する汎用テキストユーティリティを提供します。

## Quick Start

提供されている決定論的スクリプト `scripts/case_converter.py` を用いて、テキストのケース変換を実行する。

## Available Tasks

### Task 1: 変換要求の解析 *(Tool: `references/case-conversion-types.md`)*

対象となる文字列および希望する変換形式（uppercase, lowercase, camelCase, snake_case 等）をユーザーリクエストから抽出する。

### Task 2: 変換タイプの決定 *(Tool: `references/case-conversion-types.md`)*

`references/case-conversion-types.md` を参照し、ユーザーの意図に合致する変換タイプ（`upper`, `lower`, `camel`, `snake` 等）を特定する。

### Task 3: ケース変換スクリプトの実行 *(Tool: `scripts/case_converter.py`)*

抽出した文字列と特定したタイプを指定し、`scripts/case_converter.py --text <target_string> --type <determined_type>` を実行する。

### Task 4: 変換結果の提示

変換後の文字列をユーザーに提示する。

## Usage Scenarios & Trigger Examples

このスキルは以下のようなリクエストでトリガーされる：

- "このテキストを大文字に変換して: 'hello world'"
- "文字列 'MyString' を小文字にしてください"
- "'convert this to camel case' をキャメルケースに変換"
- "スネークケースに変換: 'This is a test string'"
- "テキストのケースを変換したい"

## Bundled Resources

### `scripts/` (Executable Tools)
- **`scripts/case_converter.py`**: 入力文字列と変換タイプを受け取り、変換結果を決定論的に出力する CLI スクリプト

### `references/` (On-Demand Knowledge)
- **`references/case-conversion-types.md`**: 各ケースタイプの定義と仕様を説明する参照ドキュメント

## Guidelines & Best Practices

- 変換対象の文字列が明確に指定されていることを確認すること。
- 複数の変換タイプが指定された場合は、ユーザーに優先順位を確認すること。
- スクリプトは `--help` でオプションを確認した上で直接コマンドラインから実行すること。

