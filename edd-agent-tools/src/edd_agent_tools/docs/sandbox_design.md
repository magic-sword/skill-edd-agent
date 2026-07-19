# Gymnasium 互換サンドボックス環境と永続化モデル設計 (Sandbox Design)

本ドキュメントでは、自動コード生成エージェントやテスト実行器が、安全かつ高速に試行錯誤するための「Gymnasium 互換のサンドボックスシミュレーション環境」および「本番への差分適用（永続化）モデル」の具体的な仕様について記述します。

---

## 1. テスト検証と本番適用の完全分離

AIエージェントによる自動コード書き換え時の安全性と信頼性を最大化するため、**「隔離された環境でのテスト検証（シミュレーション）」** と **「本番への変更の書き戻し（永続化）」** の責務を明確に分離しています。

*   **テスト検証 (LocalWorkspaceEnv / GitSandbox)**:
    エージェントがコードを書き換えてテストを回す作業は、本番ディレクトリから OS の一時ディレクトリ領域（`/tmp` 等）に複製された **一時サンドボックス環境内で 100% 隔離して実行** されます。本番コードが直接汚染されることはありません。
*   **本番適用 (LocalFileApplier)**:
    サンドボックス内での検証（pytest等）に 100% 合格し、安全が確認された段階で、一時環境から抽出された変更差分（`WorkspaceArtifacts`）のみをアプライヤーを用いて明示的に本番に書き戻します。

---

## 2. Git による高速ステート管理と差分抽出

一時サンドボックス内は自動的に Git 管理され、以下の恩恵を受けられます。
*   **高速ロールバック**: `reset()` 時に `git reset --hard` / `git clean` を実行し、一瞬で初期状態へ復元します。
*   **完璧な差分抽出**: `git status` を解析し、バイナリや文字コードの制約なく、新規・変更・削除されたファイルを正確に追跡します。

---

## 3. ホスト仮想環境の共有オプション (`use_host_venv`)

サンドボックス起動のたびに `pip install` が走るオーバーヘッドを解消するため、親プロジェクトの既存の `.venv` の Python インタプリタを共有してテストを実行するオプションを提供します。

---

## 4. 実行環境の抽象化プロトコル (`WorkspaceEnvProtocol`)

スキルやエージェントが動作するために要求するワークスペース環境の操作は、**`WorkspaceEnvProtocol`** プロトコルとして抽象化されています。これにより、テストと本番直接適用を透過的に切り替える（DI）ことができます。

*   **`LocalWorkspaceEnv` (一時サンドボックス環境)**:
    一時ディレクトリに複製した環境で安全にテストを検証する環境クラス。
*   **`RealWorkspaceEnv` (本番直接操作環境)**:
    隔離を行わず、指定された `workspace_dir` に対する直接の読み書き、および pytest の直接実行を行う環境クラス（直接適用ルート）。

---

## 5. CLI ランナーでの自動インジェクションと切り替え

スキル関数の引数名が `env` / `environment` であるか、型ヒントに `WorkspaceEnvProtocol` が指定されている場合、CLI ランナー（`edd_agent_tools.run`）は実行環境を自動構築して注入します。

また、CLI のオプションから環境の挙動を直接切り替えることができます。
*   `--env` / `-e`: `sandbox`（デフォルト）または `real`。使用する具象環境クラスを切り替えます。
*   `--workspace-dir` / `-w`: 基準となるワークスペースのパス（デフォルトは `.`）。
*   `--apply`: `--env sandbox` でスキル関数が例外なく正常に完了した場合に、自動的に本番へ変更差分を書き戻します（安全な自動適用）。

### コマンド実行例:
```bash
# 安全なサンドボックスで検証し、テスト成功時のみ自動適用する
python3 -m edd_agent_tools.run my-skill my_func --env sandbox --apply --workspace-dir /my/project

# 本番環境で直接実行する
python3 -m edd_agent_tools.run my-skill my_func --env real --workspace-dir /my/project
```

---

## 6. 利用コード例

```python
from edd_agent_tools import (
    LocalWorkspaceEnv, 
    RealWorkspaceEnv, 
    WorkspaceEnvProtocol,
    LocalFileApplier
)
from edd_agent_tools.evaluation.models import WriteFileAction, RunPytestAction

# 1. 依存性注入 (DI) を用いた透過的なスキル関数の実装例
def refactor_code(env: WorkspaceEnvProtocol, file_path: str):
    # 環境の種類を意識せず、共通のプロトコルで操作可能
    env.step(WriteFileAction(path=file_path, content="def improved_logic(): pass"))
    obs, _, terminated, _, _ = env.step(RunPytestAction())
    return terminated

# 2. 隔離された一時環境での呼び出し例 (トランザクション適用)
env_sandbox = LocalWorkspaceEnv(workspace_dir="/workspace/my_project")
env_sandbox.reset()

success = refactor_code(env_sandbox, "src/logic.py")

# 差分（成果物）の抽出と本番適用
if success:
    artifacts = env_sandbox.export_artifacts()
    applier = LocalFileApplier(target_dir="/workspace/my_project")
    applier.apply(artifacts)

env_sandbox.close()

# 3. 本番直接操作環境での呼び出し例 (直接書き換え)
env_real = RealWorkspaceEnv(workspace_dir="/workspace/my_project")
env_real.reset()

refactor_code(env_real, "src/logic.py") # 本番ファイルが直接書き換わります
env_real.close()
```
