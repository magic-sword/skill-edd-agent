---
name: test-executor
description: 指定されたスキルのADK evalテストセットを実行し、合格閾値に基づいて合否判定を行います。デッドロック防止のタイムアウト機能を備えています。
---

# test-executor スキル

このスキルは、指定されたテストケース定義ファイル（`*.evalset.json`）を読み込み、ハング対策を施した安全なサブプロセス環境で `adk eval` を実行します。

## 使用方法

スクリプト `scripts/execute_test.py` を呼び出して、テストを実行します。

### 引数

- `skill_name` (必須): テスト対象のスキル名。
- `eval_set_path` (必須): テストケースファイル（`*.evalset.json`）の絶対パス、または `src` ディレクトリからの相対パス。
- `--threshold_accuracy` (任意): 合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは `1.0` (100%合格)。
- `--timeout_seconds` (任意): テスト実行のタイムアウト制限（秒）。デフォルトは `180` 秒。

### 例

- **単体テストの実行（100%合格が条件）**:
  ```bash
  python src/skills/test-executor/scripts/execute_test.py \
    --skill_name text-formatter \
    --eval_set_path src/skills/text-formatter/tests/text_formatter_eval_set.evalset.json
  ```

- **トリガー精度の実行（90%以上の合格率が条件、タイムアウト120秒制限）**:
  ```bash
  python src/skills/test-executor/scripts/execute_test.py \
    --skill_name text-formatter \
    --eval_set_path src/skills/text-formatter/tests/text_formatter_trigger_eval.evalset.json \
    --threshold_accuracy 0.90 \
    --timeout_seconds 120
  ```

## AIエージェント向け使用方法 (run_skill_script)

このスキルを実行する際は、`run_skill_script` ツールを使用して、必ず以下の引数構造（JSON）で実行してください。入力・出力はJSONファイルを介してパスでやり取りします。

```json
{
  "skill_name": "test-executor",
  "file_path": "scripts/execute_test.py",
  "args": {
    "--input_json": "/workspace/src/.workflow_tmp/<スキル名>/<入力ファイル名>.json",
    "--output_json": "/workspace/src/.workflow_tmp/<スキル名>/<出力ファイル名>.json"
  }
}
```
