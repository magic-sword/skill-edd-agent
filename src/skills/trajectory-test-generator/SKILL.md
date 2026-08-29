---
name: trajectory-test-generator
description: "SKILL.mdをインプットとして、ユーザー発話、中間ツール呼び出し期待値（tool_uses）、および期待される最終応答を保持するTrajectoryEvalSetフォーマットのテストケースJSONを生成するスキル。"
pattern: workflow
license: Complete terms in LICENSE.txt
---

# スキル仕様書: trajectory-test-generator

## 概要

指定されたスキルの `SKILL.md` および `scripts/` コードを解析し、Google ADK 軌跡シミュレーション標準に準拠した `TrajectoryEvalSet` フォーマットのテストケース JSON（`[skill_name]_trajectory.evalset.json`）を生成します。

### 主な機能
* 対象スキルの仕様情報（関数名・引数・制約事項）を読み込みます。
* 会話形式（マルチターン/単一ターン）におけるユーザーの発話プロンプト、中間ツール呼び出し（`tool_uses`: ツール名と引数マッピング）、およびモデルの最終期待応答を構成します。
* 生成結果を Pydantic モデル（`TrajectoryEvalSet`）でバリデーションし、指定されたファイルパスに保存します。

---

## トリガー条件

- 「[スキル名]の軌跡テストケース（trajectory）を生成してほしい」
- 「[スキル名]のツール順序評価セットを[出力パス]に作成して」

---

## 公開関数

### generate_tests

指定されたスキルの仕様に基づき、`TrajectoryEvalSet` フォーマットのテストケース JSON を生成して保存します。

#### 入力パラメータ
| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| skill_name | str | はい | テストケースを生成する対象スキルの論理名。 |
| output_path | str | はい | 生成結果を書き出す JSON ファイルの絶対パス。 |

#### 出力仕様
* **戻り値**: `bool` (成功時: `True`, 失敗時: `False`)

