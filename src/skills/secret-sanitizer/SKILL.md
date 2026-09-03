---
name: secret-sanitizer
description: |
  Detects and masks sensitive credentials (API keys, JWT tokens, passwords, email addresses, IP addresses) in text strings or code files.
  Use when the user asks to sanitize logs, mask confidential credentials, or prepare snippets for sharing.
  Do NOT use for encryption/decryption tasks or simple single-character replacements.
license: MIT
allowed-tools: run_skill_script load_skill_resource
pattern: task_based
---

# Secret Sanitizer

## When to use
- ログファイルや設定ファイルから API キーやパスワード、トークンを安全にマスキングしたい時
- コードや設定スニペットを共有する前に機密情報（JWT、Bearerトークン等）をマスクしてほしい時
- "Sanitize passwords and email addresses in this text file" などの機密除去要求を処理する時

## When NOT to use
- 単純な1箇所の固定文字列置換（エディタの置換等で即座に完結する場合）
- 暗号化・復号処理や、ハッシュ値生成、証明書生成などの暗号学的処理
- スキル自体のテスト実行、失敗診断、自己修復、Tier昇格（`skill-evolver` を使用すること）
- スキル雛形生成やパッケージ化作業（`skill-creator` を使用すること）

## Workflow
1. 検査対象とオプションの決定: 入力データ（文字列引数またはファイルパス）、マスキング対象の機密種別（`api_key`, `bearer_token`, `jwt`, `password`, `email`, `ipv4`）、および出力先を特定する。
2. 機密情報マスキングの実行: `scripts/secret_sanitizer.py` を呼び出してマスキング処理を実行する。
   ```bash
   # 文字列の直接マスキング
   python scripts/secret_sanitizer.py --input "<raw_text>"

   # ファイルのマスキングと別ファイルへの出力
   python scripts/secret_sanitizer.py --file config.env --output config.sanitized.env

   # 特定の機密種別のみを指定してマスキング
   python scripts/secret_sanitizer.py --file log.txt --types api_key jwt password --output sanitized.log
   ```
3. 結果の確認: 機密情報がプレースホルダー（例: `<API_KEY: ********>`）に置換され、文脈やコード構造が維持されていることを確認する。

## Examples
- Input: "Sanitize 'api_key: sk-1234567890abcdef1234' in this string" → Output: "api_key: <API_KEY: ********>"
- Input: "Mask email address 'admin@company.example.com' in string" → Output: "<EMAIL: ********>"
- Input: "Mask password in 'password = mySecretPass123'" → Output: "password = <PASSWORD: ********>"

## Output format
- 単一文字列のマスキング時はプレースホルダー（例: `<API_KEY: ********>`）を適用した文字列を直接返答する。
- ファイルマスキング時は出力先ファイルパスおよび検知された機密種別のサマリーを提示する。

## Anti-patterns to avoid
- スクリプトの中身を無駄に読み込んでコンテキストを浪費しないこと（`--help` で引数仕様を確認する）。
- ファイル一括マスキング時に入力ファイルのサンプリング確認を行わずにいきなり元ファイルを上書きしないこと。
- 機密箇所以外のインデントやコード構文を破壊しないこと。

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
