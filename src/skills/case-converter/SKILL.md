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

Execute standard operations using the provided modular tools and scripts.

## Available Tasks

### Task 1: 変換要求を解析 *(Tool: `references/case-conversion-types.md`)*

To identify the target string and desired conversion type, parse the user's request.

### Task 2: 変換タイプを決定 *(Tool: `references/case-conversion-types.md`)*

To determine the specific case conversion type, match the user's intent with available options.

### Task 3: ケース変換スクリプトを実行 *(Tool: `scripts/case_converter.py`)*

To convert the string, execute scripts/case_converter.py with --text <extracted_string> and --type <determined_type>.

### Task 4: 変換結果を出力

To present the result, output the converted string to the user.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:

- "このテキストを大文字に変換して: 'hello world'"
- "文字列 'MyString' を小文字にしてください"
- "'convert this to camel case' をキャメルケースに変換"
- "スネークケースに変換: 'This is a test string'"
- "テキストのケースを変換したい"

## Bundled Resources

### `scripts/` (Executable Tools)
Deterministic execution scripts that run directly in the environment:

- **`scripts/case_converter.py`**: 入力文字列と変換タイプ（upper, lower, camel, snake）を受け取り、変換結果を返すPythonスクリプト。

### `references/` (On-Demand Knowledge)
Documentation and schema specifications loaded only when explicitly needed:

- **`references/case-conversion-types.md`**: 各ケースタイプの定義と使用例を説明するドキュメント。AIがユーザーに説明する際に参照する。

## Guidelines & Best Practices

- 変換対象の文字列は、明確に指定されていることを確認する。
- 複数の変換タイプが指定された場合は、ユーザーに優先順位を確認する。
- スクリプトは、一般的なASCII文字セットに対応していることを前提とする。
