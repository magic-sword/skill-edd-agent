---
name: tier2-test-runner
description: "指定されたスキルに対して contract, golden, judge テストを実行し、すべて成功した場合はスキルをTier 2として登録するワークフロー。"
---

# ワークフロー仕様書: tier2-test-runner

## 概要

スキルをTier 2として登録するために、契約テスト、ゴールデンテスト、ジャッジテストを自動実行し、結果に基づいて登録の可否を判定します。

### 主な機能
* 指定されたスキルに対する契約テストの実行
* ゴールデンテストケースの自動生成と実行
* ジャッジテストケースの自動生成と実行
* すべてのテスト結果の集計と評価
* すべてのテストが成功した場合のスキルのTier 2登録

### 内部処理の流れ
1. run-contract-test: 指定されたスキルに対して契約テスト（単体テスト）を実行し、基本的な機能と仕様への準拠を確認します。
2. generate-golden-tests: スキルのゴールデンテストケースを自動生成します。
3. execute-golden-tests: 生成されたゴールデンテストを実行し、スキルの期待される振る舞いを検証します。
4. generate-judge-tests: スキルのジャッジテストケースを自動生成します。
5. execute-judge-tests: 生成されたジャッジテストを実行し、より複雑なシナリオやエッジケースでの性能を評価します。
6. aggregate-results-and-register: 契約テスト、ゴールデンテスト、ジャッジテストのすべての実行結果を集計します。すべてのテストが成功した場合、対象スキルをTier 2として登録し、ワークフローの最終結果（status, message, registered）を返します。


---

## トリガー条件

このワークフローは、以下の条件やプロンプトでトリガーされます。

- 「[スキル名] をTier 2として登録してください」
- 「[スキル名] の品質評価とTier 2登録を実行してください」
- 「新しいスキル [スキル名] のテストとTier 2昇格プロセスを開始してください」

---

## 実行方法

このワークフローは、複数の処理ノードをパイプラインで実行する自律接続システムです。
以下の順番でステップが接続・順次実行されます：

1. **run-contract-test** (skill): import-validator
1. **generate-golden-tests** (skill): golden-test-generator
1. **execute-golden-tests** (skill): golden-test-executor
1. **generate-judge-tests** (skill): judge-test-generator
1. **execute-judge-tests** (skill): judge-test-executor
1. **aggregate-results-and-register** (function): 契約テスト、ゴールデンテスト、ジャッジテストの実行結果を集計し、すべて成功した場合はスキルをTier 2として登録します。最終的なワークフローの出力（status, message, registered）を設定します。

引数パラメータが入力されると、STARTノードから順に状態（tool_context.state）を伝播しながら処理が進みます。

---

## 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill | str | はい | 検証および昇格対象のスキル名。 *(制約: パターン: `^[a-z0-9-]+$`, 最小長: 3, 最大長: 50)* |

---

## 出力仕様

*   **出力モード**: `STRUCTURED_JSON`
*   **詳細**: 特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。

### 出力パラメータ (構造化JSONの戻り値構造)

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| status | Literal['success', 'failed'] | はい | 実行結果のステータス。'success' または 'failed' |
| message | str | はい | 実行結果の詳細メッセージ |
| registered | bool | はい | 登録が成功したかどうかの真偽値 |


---



---

**開発者向け注記**:
この仕様書は `skill-spec-writer` スキルによって自動生成されました。
最新の情報は `design.json` を参照し、変更は `design.json` に直接加えてください。