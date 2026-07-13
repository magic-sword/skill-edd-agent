# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

> [!NOTE]
> 具体的な利用例や API 仕様は、本パッケージの各主要クラス（`Skill`, `SkillsState`, `SkillEval` 等）の Docstring 内にサンプルコード（`Examples:`）として実装と一体で記述されています。

---

## 1. コア設計思想 (Core Design Philosophy)

本プロジェクトの実装および設計において、厳格に遵守すべき基本方針です。

*   **規約による設定 (Convention over Configuration)**:
    すべてのスキル・エージェントは統一されたファイル構成およびインターフェース規約に従います。動的インプロセスロードの窓口は `scripts/__init__.py` に統一され、これにより型検証、CLIランナーの動的生成、インプロセス呼び出しが自動化されます。
*   **関心の分離 (Separation of Concerns)**:
    *   **薄いハンドラーとロジックの分離**: エントリーポイントとなる `handler.py` は自動生成されるため、手動編集は禁止です。実処理は `executor.py` 等に完全に分離します。
    *   **オブジェクト指向とモジュール分割 (単一責任の原則)**: コードの肥大化を防ぐため、役割に応じてモジュール（`client.py`, `parser.py` 等）を分割してください。
    *   **アセットの外部化**: プロンプト等はコード内に直書きせず、`assets/` ディレクトリに外部ファイル化し、`Skill` クラス経由でロードします。
*   **明示的な入力と構造化フィードバック (Explicit Input & Structured Feedback)**:
    パラメータの受け渡しは関数の引数レベルで明示的に定義します。また、実行結果の検証性を高めるため、結果のサマリーや各種メタデータは Pydantic モデル（`Output`）として返してください。
*   **コンテキストのクリーン化 (Clean Context)**:
    プロンプト内に巨大データを直接埋め込んで結合することを禁止します。ハルシネーションを防ぐため、`GeminiContentBuilder` で添付テキストパーツとして分離送信します。

---

## 2. スキルおよびエージェントの定義規約 (Convention)

### ① スキルの「マイクロサービス化」と複数ツールの公開規約
ADK 2.0 の思想において、1つのスキルパッケージは「1つのマイクロサービス」として設計されます。

*   **ドメインの凝集とコード共有**:
    共通のデータ構造（例: `skills_state.json` の操作）や共通ロジックを持つ関連機能は、コード重複を防ぐために1つのスキルパッケージ内に集約します。
*   **エンドポイント（複数ツール）の公開**:
    スキルパッケージは、複数の関連する公開関数（APIエンドポイントに相当。例: `register_skill`, `delete_skill`）を `scripts/handler.py` に定義し、`scripts/__init__.py` から同時にエクスポートできます。
*   **遅延ロードと API 宣言の厳格化**:
    `scripts/__init__.py` は遅延ロード規約に従い、`__getattr__` による動的解決と、**`__all__` による公開API（関数群と `Output`モデル）の明示的宣言**を必須とします。
    *   `__all__` 定義が欠落している場合、または `__all__` に公開関数が1つも含まれない場合、フレームワークはロード時に即座に `AttributeError` を投げてクラッシュさせます（暗黙的なフォールバックの完全排除）。
*   **ツール名の一致**:
    ロードされた各関数は、`__all__` に宣言された関数名のまま個別の `FunctionTool` として抽出・登録されます（スキル名への動的な書き換えは行いません）。
    *   ※エクスポートされる関数が複数ある場合に `Skill.get_tool()` を呼ぶと、バグ混入を未然に防ぐために `ValueError` が投げられます。複数のツールを扱う場合は、必ず `get_tools()` を使用してください。

### ② ビジネスロジック実装規約 (`scripts/executor.py` と `models.py`)
*   **薄いハンドラーとエグゼキューターの分離**: エントリーポイントとなる `handler.py` は自動生成されるため、手動編集は禁止です。実処理は `executor.py` 内の `SkillExecutor` クラスに完全に分離します。
*   **models.py による循環参照の防止**: `handler.py` と `executor.py` が互いに参照し合って循環参照を起こすのを防ぐため、出力モデルの定義は必ず `models.py` という独立した下流ファイルに配置します。

### ③ 実行形式の分類規約 (`execution_type`)
`design.json` で定義される `execution_type` は、スキルの動作モデルおよびアセット設計の方針を決定する極めて重要なパラメータです。必ず以下の規約に従って適切に分類・指定してください。

*   **`tool` (決定論的スクリプト処理形式)**:
    *   **特性**: ファイル操作やAPIリクエストなどの「決定論的（確定）なシステム操作」を行う処理。LLMによる自律推論は含まず、Pythonスクリプト等のコードで完結させます。
    *   **design.jsonの定義**: `"execution_type": "tool"`
    *   **アセット規約**: スキル仕様書（`SKILL.md`）には、AIが引数を正しく決定できるよう「厳格なパラメータ型定義」のみを記述し、AI向けの手順指示（Instructions）などは最小限に留めます。これにより、AIが仕様書をロードする際の**無駄なトークン消費を抑え、パラメータ決定への注意力を最大化**させます。
*   **`agent` (自律思考・推論処理形式)**:
    *   **特性**: 複雑な課題（設計、コード生成など）を、別の「LLMによる自律思考を持ったエージェント（Sub-Agent）」に委譲して解決する処理。内部プロンプトに沿ってLLMが推論を実行します。
    *   **design.jsonの定義**: `"execution_type": "agent"`
    *   **アセット規約**: スキル仕様書（`SKILL.md`）には、AIがサブエージェントの思考プロセスを正しく把握できるよう「自律的な推論ステップ（Instructions）」を明記します。これにより、AIはこれが単なる機械的ツールではなく「仕事を委譲すべき自律的なエージェント」であると正しく認識し、適切なコンテキストを伝搬して呼び出せるようになります。

### ④ コーディング規約とドキュメンテーション (Docstring)

*   **Google Python Style Guide への準拠**:
    本パッケージのすべての Python コードは、**Google Python Style Guide（グーグル Python コーディング規約）** に準拠して記述します。
*   **Docstring の構造化**:
    クラスや関数の定義には、必ず Google スタイル（`Args`, `Returns`, `Raises`）の Docstring を記述してください。
*   **利用例のコード内統合**:
    二重管理を防ぐため、静的ドキュメントでの利用例の個別管理は行いません。すべての主要クラス・公開 API には、Docstring 内に **`Examples:`** セクションを作成し、doctest 形式で動作するサンプルコードを必ず記述してください。

### ⑤ 新規スキル作成時のパス自動解決規約
*   **物理仮登録不要のパス特定**:
    ディスク上および `skills_state.json` にまだ登録されていない完全な新規スキル名が指定された場合、`SkillsState` は `skills_state.json` の `entries` 内の最優先パス（`entries` の最初のパス。未存在時はカレントディレクトリ `.`）を基点として、暫定の出力先ディレクトリ（例: `src/skills/[スキル名]`）を自動解決します。これにより、事前登録の手間なく透過的な「設計 ➡ コード生成 ➡ 自動テスト」の一気通貫フローが自動化されます。

---

## 3. 主要クラスの役割

*   **`Skill` / `SkillsState`**:
    スキルのルート、アセット、ソースコードパスの自動解決、インプロセス動的ロード（`load_module()`）、FunctionToolオブジェクトの生成、およびプロンプトなどのアセットファイルの安全ロード。さらに、`SkillsState` を用いた合格スキルの自動プロモート（マウント）管理。また、物理的・論理的登録がない新規スキル名に対しても、最優先探索エントリに基づく暫定パスの自動解決・フォールバック機能を提供します。
*   **`SkillEval` / `UnitEval` / `TriggerEval`**:
    スキルの評価（ユニットテスト、トリガーテストなど）を管理するクラス群。アセットパス（`*.evalset.json`、`*.evalset.config.json`）の解決、テストケースの保存、およびデフォルト設定ファイルの自動生成などの役割を担います。
*   **`GeminiClient` / `GeminiRequest`**:
    自動リトライとモデル中央管理を備えた共通クライアントおよびリクエストオブジェクト。以下のように流れるようなメソッドチェーンでリクエストの構築と実行を行います。
    ```python
    from edd_agent_tools.gemini import GeminiClient
    client = GeminiClient()
    response = client.request("プロンプト").add_dir("dir/").execute()
    ```
*   **`LibraryDocumentationReader`**:
    本ドキュメント（README.md）を動的にロードし、LLMのシステムプロンプト等に開発規約として添付可能にする。

---

## 4. 日本語テスト実行パッチ (Monkey Patch)
ADK 2.0 評価器（Rouge-1）の日本語文字分割問題を解決するため、`bert-base-multilingual-cased` による多言語トークナイズパッチを `adk eval` 実行時に自動適用します。

---

## 5. Gymnasium 互換サンドボックス環境と永続化モデル

本パッケージは、自動コーディングエージェントやリファクタリングスキルが安全かつ高速に試行錯誤できる「Gymnasium 互換のサンドボックスシミュレーション環境」および「本番への差分適用（永続化）モデル」を提供します。

### ① 関心の分離：テスト検証と本番適用の明確な分離
AIエージェントによる自動コード書き換え時の安全性と信頼性を最大化するため、**「隔離された環境でのテスト検証（シミュレーション）」** と **「本番への変更の書き戻し（永続化）」** の責務を明確に分離しています。

*   **テスト検証 (LocalWorkspaceEnv / GitSandbox)**:
    エージェントがコードを書き換えてテストを回す作業は、本番ディレクトリから OS の一時ディレクトリ領域（`/tmp` 等）に複製された **一時サンドボックス環境内で 100% 隔離して実行** されます。本番コードが直接汚染されることはありません。
*   **本番適用 (LocalFileApplier)**:
    サンドボックス内での検証（pytest等）に 100% 合格し、安全が確認された段階で、一時環境から抽出された変更差分（`WorkspaceArtifacts`）のみをアプライヤーを用いて明示的に本番に書き戻します。

### ② Git による超高速ステート管理と差分抽出
一時サンドボックス内は自動的に Git 管理され、以下の恩恵を受けられます。
*   **高速ロールバック**: `reset()` 時に `git reset --hard` / `git clean` を実行し、一瞬で初期状態へ復元します。
*   **完璧な差分抽出**: `git status` を解析し、バイナリや文字コードの制約なく、新規・変更・削除されたファイルを正確に追跡します。

### ③ ホスト仮想環境の共有オプション (`use_host_venv`)
サンドボックス起動のたびに `pip install` が走るオーバーヘッドを解消するため、親プロジェクトの既存の `.venv` の Python インタプリタを共有してテストを実行するオプションを提供します。

### ④ 実行環境の抽象化プロトコル (`WorkspaceEnvProtocol`)
スキルやエージェントが動作するために要求するワークスペース環境の操作は、**`WorkspaceEnvProtocol`** プロトコルとして抽象化されています。これにより、テストと本番直接適用を透過的に切り替える（DI）ことができます。

*   **`LocalWorkspaceEnv` (一時サンドボックス環境)**:
    一時ディレクトリに複製した環境で安全にテストを検証する環境クラス。
*   **`RealWorkspaceEnv` (本番直接操作環境)**:
    隔離を行わず、指定された `workspace_dir` に対する直接の読み書き、および pytest の直接実行を行う環境クラス（直接適用ルート）。

### ⑤ CLI ランナーでの自動インジェクションと切り替え
スキル関数の引数名が `env` / `environment` であるか、型ヒントに `WorkspaceEnvProtocol` が指定されている場合、CLI ランナー（`edd_agent_tools.run`）は実行環境を自動構築して注入します。

また、CLI のオプションから環境の挙動を直接切り替えることができます。
*   `--env` / `-e`: `sandbox`（デフォルト）または `real`。使用する具象環境クラスを切り替えます。
*   `--workspace-dir` / `-w`: 基準となるワークスペースのパス（デフォルトは `.`）。
*   `--apply`: `--env sandbox` でスキル関数が例外なく正常に完了した場合に、自動的に本番へ変更差分を書き戻します（安全な自動適用）。

#### コマンド実行例:
```bash
# 安全なサンドボックスで検証し、テスト成功時のみ自動適用する
python3 -m edd_agent_tools.run my-skill my_func --env sandbox --apply --workspace-dir /my/project

# 本番環境で直接実行する
python3 -m edd_agent_tools.run my-skill my_func --env real --workspace-dir /my/project
```

### ⑥ 利用コード例

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

---

## 6. 前提条件と動作環境 (Prerequisites)

本ライブラリは、Pydanticモデルの `StrEnum` などの機能を使用しているため、以下の環境が必要です。
*   **Python**: `>= 3.11` (Python 3.11 以上を必須とします)

