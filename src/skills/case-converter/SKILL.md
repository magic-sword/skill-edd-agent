---
name: case-converter
description: This skill should be used when a user requests to convert a given string into a specific case format, such as uppercase, lowercase, camelCase, or snake_case. It provides a utility for common text case transformations.
license: Complete terms in LICENSE.txt
pattern: task_based
---

# Case Converter

## Overview

このスキルは、入力された文字列を大文字、小文字、キャメルケース、スネークケースのいずれかに変換する汎用的なテキストユーティリティを提供します。

## Quick Start

Execute standard operations using the provided modular tools and scripts.

## Available Tasks

### Task 1: 入力の解析

To identify the input string and target case, parse the user's prompt.

### Task 2: ケース変換の実行 *(Tool: `scripts/convert_case.py`)*

To perform the case conversion, execute scripts/convert_case.py with the identified text and case type.

### Task 3: 結果の提示

To present the result, output the converted string to the user.

## Usage Scenarios & Trigger Examples

This skill is triggered when handling requests such as:

- "このテキストを大文字に変換して: 'hello world'"
- "指定された文字列を小文字にしてください: 'HELLO WORLD'"
- "キャメルケースに変換してほしい: 'hello world example'"
- "スネークケースに変換して: 'Hello World Example'"
- "文字列 'MyString' を全て小文字に変換してください。"

## Bundled Resources

### `scripts/` (Executable Tools)
Deterministic execution scripts that run directly in the environment:

- **`scripts/convert_case.py`**: 入力された文字列を指定されたケース形式（upper, lower, camel, snake）に変換するPythonスクリプト。

### `references/` (On-Demand Knowledge)
Documentation and schema specifications loaded only when explicitly needed:

- **`references/case-conversion-guide.md`**: 各ケース変換形式（キャメルケース、スネークケースなど）の定義と具体的な変換ルールの説明。LLMが変換ロジックを理解するのに役立つ。

## Guidelines & Best Practices

- 入力文字列が提供されていない場合は、ユーザーに明確な文字列の入力を求めること。
- サポートされていない変換形式が要求された場合は、利用可能な形式を提示し、再入力を促すこと。
- 変換結果は、ユーザーが理解しやすい形式で簡潔に提示すること。
