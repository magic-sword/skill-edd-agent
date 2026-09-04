# 決定論的サンドボックス環境と評価基盤設計 (Sandbox Design)

本ドキュメントでは、AIエージェントやテスト実行器が、安全かつ高速に試行錯誤・自己進化するための「決定論的サンドボックス環境（`LocalWorkspaceEnv`）」および「差分抽出・永続化モデル」の設計仕様について記述します。

---

## 1. テスト検証と本番適用の完全分離

AIエージェントによる自動コード書き換え時の安全性と信頼性を最大化するため、**「隔離された環境でのテスト検証（シミュレーション）」** と **「本番への変更の反映（永続化）」** の責務を明確に分離しています。

*   **テスト検証 (`LocalWorkspaceEnv`)**:
    エージェントがコードを書き換えてテストを回す作業は、本番ディレクトリから OS の一時ディレクトリ領域（`/tmp` 等）に複製された **一時サンドボックス環境内で 100% 隔離して実行** されます。本番コードが直接汚染されることはありません。
*   **安全な差分抽出 (`WorkspaceArtifacts`)**:
    サンドボックス内での検証（契約テスト・シミュレーション評価等）に 100% 合格し、安全が確認された段階で、一時環境から抽出された変更差分（`WorkspaceArtifacts`）のみを明示的に本番に適用・書き戻します。

---

## 2. Git による高速ステート管理と差分追跡

一時サンドボックス内は自動的に Git 管理され、以下の恩恵を受けられます：
*   **高速ロールバック**: `reset()` 時にミリ秒単位で完全に初期状態へ復元します。
*   **完全な差分抽出**: `git status` を解析し、バイナリや文字コードの制約なく、新規・変更・削除されたファイルを正確に追跡・抽出します。

---

## 3. ホスト仮想環境の共有オプション (`use_host_venv`)

サンドボックス起動のたびに `pip install` が走るオーバーヘッドを解消するため、親プロジェクトの既存の `.venv` の Python インタプリタを共有してテストを実行するオプションを提供します。

---

## 4. 実行環境の抽象化プロトコル (`WorkspaceEnvProtocol`)

スキルやエージェントが動作するために要求するワークスペース環境の操作は、**`WorkspaceEnvProtocol`** プロトコルとして抽象化されています。これにより、テストと本番直接適用を透過的に切り替える（Dependency Injection）ことができます。

*   **`LocalWorkspaceEnv` (一時サンドボックス環境)**:
    一時ディレクトリに複製した環境で安全にテストを検証する環境クラス。
*   **`RealWorkspaceEnv` (本番直接操作環境)**:
    隔離を行わず、指定された `workspace_dir` に対する直接の読み書き、および pytest の直接実行を行う環境クラス。

---

## 5. 統合 CLI (`edd`) とサンドボックス連携

統合 CLI `edd` は、動的ディスパッチ（`edd run`）や多層評価（`edd eval` / `edd optimize`）において、安全なサンドボックス環境 `LocalWorkspaceEnv` を自動的に構築して実行します。

### コマンド実行例:
```bash
# スキルのスクリプトを実行
edd run case-converter --input "hello_world" --to camel

# サンドボックス環境でスキルの契約テストを実行
edd eval case-converter --type contract

# 連鎖回帰テストと Tier 昇格判定を実行
edd tier-gate case-converter
```

---

## 6. 利用コード例

```python
from edd_agent_tools.evaluation import LocalWorkspaceEnv, ContractTestRunner
from edd_agent_tools.state import SkillsState

# 1. 隔離された一時環境（GitSandbox）の構築
env_sandbox = LocalWorkspaceEnv(
    workspace_dir="/workspace",
    target_files=["src/skills/case-converter"]
)
obs, info = env_sandbox.reset()

# 2. サンドボックス内での契約テスト・多層評価の安全な実行
state = SkillsState()
skill = state.get_skill("case-converter")

# 評価データセット（tests/*.test.json）を用いた決定論的検証
runner = ContractTestRunner()
result = runner.run_tests(
    skill=skill,
    test_cases_data=skill.tests.load_latest_report() or {},
    env=env_sandbox
)

# 3. テスト合格時の変更差分（成果物）の抽出
if result.failed == 0:
    artifacts = env_sandbox.export_artifacts()
    print("Modified files:", artifacts.modified_files)
    print("Deleted files:", artifacts.deleted_files)

# 4. サンドボックスの破棄（自動ロールバック・一時ファイル消去）
env_sandbox.close()
```
