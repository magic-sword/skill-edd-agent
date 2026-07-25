---
name: adversarial-test-executor
description: "指定されたスキルに対し敵対的・限界テストケース(EvalCaseSet)を実行し、結果(EvalRunResult)を返します。"
---

# スキル仕様書: adversarial-test-executor

## 概要

指定されたスキルに対し敵対的・限界テストケース(EvalCaseSet)を実行し、結果(EvalRunResult)を返します。

### 主な機能
* 指定されたスキルに対して敵対的・限界テストケースを実行します。
* JSON形式のEvalCaseSetファイルからテストケースを読み込みます。
* テスト実行結果をEvalRunResultオブジェクトとして返却します。
* ContractTestRunnerを利用して契約駆動テストを実行します。

### 内部処理の流れ
1. テスト対象のスキル名を元に、システムからスキルオブジェクトを取得します。
2. 指定されたファイルパスから敵対的テストケース（EvalCaseSet）のJSONデータを読み込みます。
3. 読み込んだJSONデータをEvalCaseSetオブジェクトとしてパースします。
4. ContractTestRunnerを初期化します。
5. 取得したスキルオブジェクト、パースしたテストケース、および実行環境をContractTestRunnerに渡し、テストを実行します。
6. テスト実行結果（EvalRunResult）を返却します。
7. テスト実行中にエラーが発生した場合は、エラーを捕捉し、失敗を示すEvalRunResultを生成して返却します。


---

## トリガー条件

このスキルは、以下の条件やプロンプトでトリガーされます。

- 「skill-coder」に対して敵対的テストを実行して。
- 「my-new-skill」の限界テストケースを「tests/my-new-skill_edge.evalset.json」で実行して。
- 指定されたスキルと評価セットパスを使ってテストを実行し、結果を教えてください。

---

## 公開関数

### run_tests

敵対的・限界テストを実行し、その結果(EvalRunResult)を返します。

#### 実行方法
${skill_name} は、与えられたパラメータに基づいて特定のタスクを**決定論的に実行**するツールです。LLMが推論を挟まず、直接このツールを呼び出して指示通りの操作を行います。

利用例：
${skill_name}(`skill_name`, `eval_set_path`, `env`)

#### 入力パラメータ
| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| skill_name | str | はい | - | テストを実行する対象スキルの名前。 |
| eval_set_path | str | はい | - | 敵対的テストケース(EvalCaseSet)のJSONファイルパス。 |
| env | WorkspaceEnvProtocol | はい | - | テスト実行環境。 |


#### 出力仕様
* **出力モード**: `VALUE_ONLY` (プレーンテキスト（値のみ）)
* **戻り値の型**: `EvalRunResult`

スキル実行結果を示す単一のテキストメッセージが返されます。


---



---

**開発者向け注記**:
この仕様書は `skill-spec-writer` スキルによって自動生成されました。
最新の情報は `design.json` を参照し、変更は `design.json` に直接加えてください。