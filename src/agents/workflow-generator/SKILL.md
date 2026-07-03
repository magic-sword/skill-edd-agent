---
name: workflow-generator
description: 指定されたディレクトリに、ユーザーの指示に応じた新しいワークフローエージェント（SKILL.md, scripts/workflow.py, scripts/main.py）を自動生成するスキル。
---

# ワークフロー生成エージェント

このスキルは、ユーザーの指定した要件や説明に基づいて、新しい Google ADK 互換 of ワークフローエージェント（DAG制御エージェント）を自律的に生成します。

生成されるアセットは以下の通りです：
* `SKILL.md`（YAMLフロントマター、使用手順、依存するスキル）
* `scripts/workflow.py`（エージェントおよびエッジによるDAG定義）
* `scripts/main.py`（ToolContextから情報を受け取りワークフローを非同期実行するエントリーポイント）

## 使用手順

1. **スクリプトの実行**:
   エージェントは `scripts/main.py` を実行するために `EnvironmentToolset`（`Execute`）ツールを呼び出します。
   引数として、作成したいワークフローの名前を示す `--workflow_name` と、ワークフローの要件や手順を示す `--prompt` を渡します。オプションで出力先ディレクトリ `--output_dir` や使用モデル `--model` も指定可能です。

   コマンドの実行例:
   ```bash
   python src/agents/workflow-generator/scripts/main.py \
     --workflow_name data-pipeline \
     --prompt "データを取得し、フォーマット変換を行い、要約を出力するワークフロー" \
     --output_dir src/agents/data-pipeline
   ```

2. **処理の確認**:
   スクリプトは、内部で動的に **ワークフロー開発者エージェント (WorkflowDeveloperAgent)** を起動します。このサブエージェントは自律的にファイルを書き出し、初期エラーや不具合のないワークフローエージェント一式を出力します。
   処理が正常に完了すると、指定のディレクトリに動作するワークフローエージェント一式が出力されます。

## AIエージェント向け使用方法 (FunctionTool)

このスキルをエージェントにバインドして実行する際は、インプロセスの `generate_workflow_code` 関数ツールを直接呼び出してください。
テストの自動実行および動的ロードは、エントリーポイントである `scripts/main.py` を通じて行われます。

### 入力パラメータ

| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| workflow_name | str | true | 作成するワークフローエージェントの定義名。有効な Python 識別子である必要があります（ADK 2.0 の制約によりハイフン `-` は使用できず、アンダースコア形式である必要があります。例: `data_pipeline`） |
| prompt | str | true | 生成したいワークフローの要件や手順 |
| output_dir | str | false | 生成されたワークフローの絶対出力ディレクトリパス |

### 共有セッション状態 (Session State) のインターフェース
* **入力値の読み込み**:
  * `workflow_name`: `tool_context.state` から自動取得されます。
  * `prompt`: `tool_context.state` から自動取得されます。
  * `output_dir` (任意): `tool_context.state` から自動取得されます。
* **出力値の書き込み**:
  * `workflow_dir`: 生成されたワークフローの絶対ディレクトリパスを格納します。

### 出力形式の要件 (Output Mode)
- **Output Mode: VALUE_ONLY**
  新規ワークフローエージェントの生成完了に関する決定論的なステータスメッセージのみを返却します。

## 設計方針と選定理由 (Design Policy & Rationale)

このワークフローエージェントは、1つのLLMエージェントにすべての生成タスク（設計、コード実装、DAG接続、CLIランナー引数定義、仕様書ドキュメントの作成）を一度に行わせるのではなく、**5つの特化したエージェント（ノード）にタスクを細分化し、DAG（Directed Acyclic Graph）として逐次実行するマルチエージェントシステム**として構成されています。

### 1. タスクの段階的細分化
ワークフローの自動生成は、出力するファイル数が多く、かつDAGの論理構造とCLIランナーの引数が紐付く必要があるため、非常に高負荷なタスクです。これを以下の5つの明確なステップに分割し、1エージェントあたりのタスク範囲を最小化しています。
*   **WorkflowDesignerAgent (設計)**: 要件プロンプトを分析し、必要な依存スキル、CLIパラメータ、DAGエッジ接続構造をまとめた `assets/design.json` を生成する。
*   **ToolLoaderAgent (ツール & Agent定義)**: `design.json` に基づき、`workflow.py` に `SkillRegistry` からのツールロードと各 `Agent` インスタンス定義を実装する。
*   **DagBuilderAgent (DAG構築)**: `design.json` に基づき、`workflow.py` にエッジ接続（Workflow定義）を実装し、エクスポートする。
*   **MainGeneratorAgent (エントリーポイント引数実装)**: 設計された引数リストを基に、`main.py` の `add_argument` にパラメータ定義を追加する。
*   **DocGeneratorAgent (ドキュメント生成)**: 完成したコードを解析し、YAML メタデータやパラメータ表を含んだ `SKILL.md` を完成させる。

### 2. API 制限の回避 (503 / 429 対策)
単一のエージェントに思考ループを繰り返させると、コンテキスト履歴が急速に累積して肥大化します。これが短時間での連続呼び出しと重なると、APIの RPM (Requests Per Minute) や TPM (Tokens Per Minute) 制限を超過し、サーバーから `503 UNAVAILABLE` または `429 TOO_MANY_REQUESTS` で一時ブロックされる原因となります。
タスクを分割し、各エージェントの思考ターン数を1〜2回に抑えることで、APIの負荷スパイクを回避し、安定した完走を実現しています。

### 3. 品質の向上と状態共有
エージェントの役割を「設計」「コード生成」「CLI引数」「ドキュメント」に分離することで、LLM が異なる仕様や文脈を混同するリスク（例: 実装コードと CLI 引数の不整合など）がなくなります。また、各ステップの状態は ADK 2.0 の `ToolContext.state` や `InMemorySessionService` のセッション状態で自動的に引き継がれるため、状態管理のための余計なバケツリレー制御を LLM に指示する必要がありません。

