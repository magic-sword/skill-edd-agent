---
name: first-test-runner
description: 指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録します。
---

# first-test-runner

## 概要

このワークフローは、対象スキルに対してトリガー評価、テスト実行、インポート検証、設計検証を行います。すべての検証が成功した場合、対象スキルをTier 1（READ_ONLY）としてSkillsStateに登録します。いずれかの検証が失敗した場合は、登録を行わず、失敗の詳細を返します。

### 主な機能
* 対象スキルに対するトリガー評価アセットの自動生成と実行。
* 指定された合格精度閾値に基づいたテスト実行と結果評価。
* スキルの動的ロードにおけるインポートエラーの検証。
* スキルの設計と実装の整合性検証。
* すべての検証が成功した場合、対象スキルをTier 1（READ_ONLY）として自動登録。
* 検証失敗時には、登録を行わず、失敗した検証の詳細情報を提供。

### 内部処理の流れ
1. run-trigger-evaluator: 対象スキルに対して 'trigger-evaluator' スキルを実行し、トリガーチェックのテストアセットを自動生成します。結果はワークフローの状態に保存されます。
2. run-test-executor: 対象スキルに対して 'test-executor' スキルを実行し、生成されたテストを走らせます。入力された合格精度閾値（threshold_accuracy）が使用され、結果はワークフローの状態に保存されます。
3. run-import-validator: 対象スキルに対して 'import-validator' スキルを実行し、動的ロードの検証（インポートエラーチェック）を行います。結果はワークフローの状態に保存されます。
4. run-design-validator: 対象スキルに対して 'design-validator' スキルを実行し、設計と実装の整合性を検証します。結果はワークフローの状態に保存されます。
5. evaluate-and-register-skill: 上記の各検証ステップ（トリガー評価、テスト実行、インポート検証、設計検証）の結果を評価します。すべての検証のステータスが 'success' であった場合、edd-agent-tools の 'SkillsState' を用いて、対象スキルを Tier 1 (READ_ONLY) のスキルとして登録します。いずれかの検証が失敗またはエラーが発生した場合は、登録は行わず、失敗した検証の詳細を Output に含めて返します。

## トリガー条件

- スキル 'my-new-skill' の品質検証を実行してください。
- スキル 'data-processor' をテストし、合格精度0.9以上でTier 1登録を試行してください。
- 新しいスキルをシステムに登録する前に、すべてのテストと検証を実行してください。

## AIエージェント向け使用方法

### 1. 実行手順（Instructions）

このワークフローは、複数の処理ノードをパイプラインで実行する自律接続システムです。
以下の順番でステップが接続・順次実行されます：

1. **run-trigger-evaluator** (function): trigger-evaluator スキルを実行し、結果を tool_context.state に保存します。
1. **run-test-executor** (function): test-executor スキルを実行し、結果を tool_context.state に保存します。
1. **run-import-validator** (function): import-validator スキルを実行し、結果を tool_context.state に保存します。
1. **run-design-validator** (function): design-validator スキルを実行し、結果を tool_context.state に保存します。
1. **evaluate-and-register-skill** (function): 各検証ステップの結果を評価し、すべて成功していれば対象スキルをTier 1として登録します。失敗した場合はその詳細を収集します。

引数パラメータが入力されると、STARTノードから順に状態（tool_context.state）を伝播しながら処理が進みます。

### 2. 呼び出し方法
- **インプロセス呼び出し (Python API)**: ロード関数 `process_message(params, tool_context)` を使用。
- **サブプロセス呼び出し (CLI)**: CLIランナーを使用。
  `python3 -m edd_agent_tools.run first-test-runner [オプション引数]`
- **出力形式 (Output Mode)**: `STRUCTURED_JSON` (特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。)

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill | str | はい | 試験対象のスキル名。 |
| threshold_accuracy | float | いいえ | 合格に必要な精度の閾値（0.0 から 1.0）。デフォルトは 1.0。 *(制約: 最小値: 0.0, 最大値: 1.0)* |

### 出力パラメータ (構造化JSONの戻り値構造)

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| status | Literal['success', 'failed'] | はい | ワークフローの実行結果。'success' または 'failed'。 |
| message | str | はい | 実行結果のサマリー、または不合格テストや検証エラーの詳細。 |
| registered | bool | はい | 対象スキルがSkillsStateにTier 1として登録されたかどうかの真偽値。 |


