---
name: trajectory-test-executor
description: "LocalWorkspaceEnv上でテスト対象スキルを実行し、発生したツール呼び出し履歴（ツール名・引数・実行順序）をTrajectoryEvalSetの期待値と決定論的に比較アサートしてテスト結果（EvalRunResult）を返します。"
---

# スキル仕様書: trajectory-test-executor

## 概要

`TrajectoryEvalSet` 形式のテストケース JSON ファイルを読み込み、指定されたサンドボックス環境（`LocalWorkspaceEnv`）上でスキルのツール実行シーケンスをシミュレート・アサートします。

### 主な機能
* `TrajectoryEvalSet` 形式のテストケースのロードとパース。
* スキル実行時のツール呼び出し（ツール名・引数・順序）のトレース記録。
* 期待値（`expected_tool_uses`）との **決定論的アサーション**（`EXACT` 完全一致 または `IN_ORDER` 順序保持一致）。
* 詳細な評価ログのファイル保存および `EvalRunResult` （合格率スコア）の出力。

---

## トリガー条件

- 「[スキル名]の軌跡テストを[評価セットパス]で実行してください」
- 「[スキル名]のツール順序アサーションテストを実行したい」

---

## 公開関数

### run_tests

指定されたスキルと `TrajectoryEvalSet` ファイルに基づき、決定論的なツール軌跡テストを実行します。

#### 入力パラメータ
| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill_name | str | はい | テスト対象スキルの論理名。 |
| eval_set_path | str | はい | `TrajectoryEvalSet` 形式の JSON ファイルパス。 |
| env | WorkspaceEnvProtocol | はい | サンドボックス実行環境。 |

#### 出力仕様
* **戻り値**: `EvalRunResult` (合格数、不合格数、精度スコア含む)
