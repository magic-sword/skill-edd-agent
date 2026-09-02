---
name: secret-sanitizer
description: |
  Detects and masks sensitive credentials (API keys, JWT tokens, passwords, email addresses, IP addresses) in text strings or code files.
  Use when the user asks to sanitize logs, mask confidential credentials, or prepare snippets for sharing.
  Do NOT use for encryption/decryption tasks or simple single-character replacements.
license: MIT
pattern: task_based
---

# Secret Sanitizer

## Overview

文字列やテキストファイル内に含まれる API キー、Bearer トークン、JWT、パスワード、メールアドレス、IPv4 アドレスなどの機密情報を決定論的に検出し、安全なプレースホルダーでマスキングします。

## Quick Start

文字列内の機密情報をマスキングするには、`scripts/secret_sanitizer.py` を呼び出す：

```bash
python scripts/secret_sanitizer.py --input "Connect with api_key: sk-1234567890abcdef1234 and email: admin@example.com"
# Output: Connect with api_key: <API_KEY: ********> and email: <EMAIL: ********>
```

## Available Tasks

### Task 1: 検査対象とオプションの決定
入力データ（文字列引数またはファイルパス）、マスキング対象の機密種別（`api_key`, `bearer_token`, `jwt`, `password`, `email`, `ipv4`）、および出力先を特定する。

### Task 2: 機密情報マスキングの実行 *(Tool: `scripts/secret_sanitizer.py`)*
`scripts/secret_sanitizer.py` を実行してマスキング処理を行う：

```bash
# 文字列の直接マスキング
python scripts/secret_sanitizer.py --input "<raw_text>"

# ファイルのマスキングと別ファイルへの出力
python scripts/secret_sanitizer.py --file config.env --output config.sanitized.env

# 特定の機密種別のみを指定してマスキング
python scripts/secret_sanitizer.py --file log.txt --types api_key jwt password --output sanitized.log
```

### Task 3: 結果の確認
機密情報がプレースホルダー（例: `<API_KEY: ********>`）に置換され、文脈やコード構造が維持されていることを確認する。

## Usage Scenarios & Trigger Examples

- "このログファイルから API キーやパスワードをマスキングして"
- "コードを共有する前に機密情報（JWTやトークン）をマスクしてほしい"
- "Sanitize passwords and email addresses in this text file"

## When NOT to Use This Skill

Do NOT use this skill in the following scenarios (use native tools or alternative workflows instead):
- **粒度境界 (Granularity)**: 単純な 1 箇所の固定文字列置換（`sed` やエディタの置換機能で即座に完結する場合）。
- **技術的限界 (Out-of-Scope)**: 暗号化・復号処理や、ハッシュ値生成、証明書生成などの暗号学的処理（`cryptography` や専用暗号ツールを使用すること）。
- **ライフサイクル分離 (Lifecycle)**: スキル自体のテスト実行、失敗診断、自己修復、Tier昇格（`skill-evolver` を使用すること）。
- **インベントリ照合 (Inventory)**: スキル雛形生成やパッケージ化作業（`skill-creator` を使用すること）。

## Requirements & Prerequisites

本スキルは Zero-dependency ツールとして設計されており、外部パッケージの追加インストールは不要です：
- **Python**: >= 3.10 (Python 標準ライブラリのみで動作)

## Bundled Resources

### `scripts/` (Executable Tools - Zero-dependency)
- **`scripts/secret_sanitizer.py`**: APIキー、トークン、パスワード、メール、IPアドレスを正規表現で検出しマスキングする Zero-dependency CLI ツール。

### `references/` (On-Demand Knowledge)
- **`references/guide.md`**: 対応機密情報パターン一覧、マスク形式仕様、およびエッジケース仕様。

### `examples/` (Usage Patterns)
- **`examples/example_usage.py`**: 各種マスキングの具体的な引数・実行パターン集。

## Guidelines & Best Practices

- **Black-box Execution**: スクリプト実行時はまず `python scripts/secret_sanitizer.py --help` でオプション仕様を確認し、コンテキスト節約のためスクリプトを直接読み込まないこと。
- **Reconnaissance First**: ファイル一括マスキング時は、まず入力ファイルのデータ構造をサンプリング確認した上で処理を実行すること。
- **Minimal Edits**: マスキング適用時は、機密箇所以外のインデントやコード構文を破壊しないこと。
- 詳細なパターン仕様は `references/guide.md`、使用例は `examples/example_usage.py` を参照する。
