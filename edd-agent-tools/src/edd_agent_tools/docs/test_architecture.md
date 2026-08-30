# ADKエージェントテスト自動化設計仕様 (Test Architecture)

本ドキュメントでは、ADK (Agent Development Kit) エージェントにおけるスキルの品質保証 (QA) を自動化するための、テストケース生成 (Generator)、シミュレーション実行 (Executor)、および Tier 昇格ゲートキーパーの標準化設計について記述します。

---

## 1. 統合評価スキル (skill-evaluator) と Progressive Disclosure 設計

### 課題
従来のスキルテストでは、テストタイプごと（Trigger, Contract, Golden, Judge, Trajectory, Adversarial）に生成スキルと実行スキルを別々のディレクトリとして過度に細分化（Micro-Skills）していたため、以下の問題が発生していました：
*   常時ロードされるスキルメタデータ（Frontmatter）が肥大化し、コンテキストウィンドウを無駄に圧迫。
*   エージェントのインテント分類において、類似するテストスキル間での競合・誤判定が発生。
*   `handler.py`, `executor.py`, `models.py` などの多層ラッパーボイラープレートが散乱。

### 解決策: 統合評価スキル (`skill-evaluator`) への一元化
すべてのテスト生成・実行・Tier 昇格判定を、単一の自己完結型メタスキル **[`skill-evaluator`](file:///workspace/src/skills/skill-evaluator)** に集約しました。

```mermaid
graph TD
    Spec[SKILL.md / scripts] -->|1. Analyze & Design| Gen["Test Authoring (references/test_types_guide.md)"]
    Gen -->|2. Save Asset| File[(tests/skill_name/test_type.evalset.json)]
    File -->|3. Read & Run| Exec["skill-evaluator (edd eval / scripts/run_eval.py)"]
    Exec -->|4. Assert & Run| Env[LocalWorkspaceEnv (Git Sandbox)]
    Env -->|5. Aggregate & Report| Result[(tests/results/latest_report.json)]
    Result -->|6. Gating & Promotion| Gate["skill-evaluator (edd tier-gate / scripts/run_tier_gate.py)"]
```

1.  **テスト設計・配置フェーズ**:
    仕様定義（`SKILL.md` や `scripts/`）を基に、指定されたテストタイプ（`trigger`, `contract`, `golden`, `judge`, `trajectory`, `adversarial`）の評価セットを設計し、`tests/<skill_name>_<type>.evalset.json` に**物理的なアセットファイルとして保存**します。エージェント自身が対話的に設計することも可能です。
2.  **評価実行フェーズ (`edd eval` / `scripts/run_eval.py`)**:
    保存された JSON 評価セットをロードし、隔離されたサンドボックス環境（`LocalWorkspaceEnv`）上でテストを実行・評価します。アセットを再利用するため、**実行フェーズは何度繰り返しても 100% 決定論的（再現可能）かつ高速・低コスト**で実行できます。結果は `latest_report.json` に構造化ログとして永続化されます。
3.  **Tier 昇格ゲートキーパーフェーズ (`edd tier-gate` / `scripts/run_tier_gate.py`)**:
    Tier 階層（Tier 1: Production, Tier 2: Verified, Tier 3: Mastered）に応じた防壁テストを一括検証し、合格時に `SkillsState` へ登録・昇格させます。


---

## 2. テスト共通スキーマと型駆動判定

テストアセットのポータビリティを確保するため、テストデータは `edd-agent-tools` で一元管理された以下の2つの主要スキーマフォーマットを使用します。

### ① スキーマ駆動テスト (Unit / Contractテスト用): `EvalCaseSet`
Pydanticモデルなどの入力バリデーション、境界値チェック、期待される例外アサーションを行うためのスキーマ。
*   **特徴**: 各パラメータ制約（`ge`, `choices` 等）違反に対する `ValidationError` などの期待される例外クラス名を `ExpectedResultType` として型制約レベルで固定し、LLM による曖昧なテキスト出力を物理的に排除した決定論的アサーションを行います。

### ② 軌跡評価テスト (インテント/シミュレーション用): `TrajectoryEvalSet`
Google ADK 公式の軌跡シミュレーションテストに準拠した、ユーザーとエージェント（ルーター）の会話ターンごとの挙動を検証するためのスキーマ。
*   **特徴**: `conversation` リストの中に、ユーザープロンプト（発話）と、それによって呼び出されるべき期待ツール（`tool_uses`）を定義し、ルーティングが誤検知なく正確に機能するかをアサーションします。
*   **負例テストの判定ロジック**: 負例テストケース（対象外のプロンプト）の検証時、ルーターが対象スキルを誤って起動しなかった場合に **合格 (PASSED)** としてアサーション判定します。

---

## 3. 仮想環境の隔離と依存性注入 (Dependency Injection)

### 課題
テスト実行器がテストのセットアップ、実行、検証（例: `pytest` の呼び出し）のためにファイルシステム操作やサブプロセス実行を OS に対して直接行うと、環境破壊や副作用のリスクが発生します。

### 解決策: 依存性注入 (Dependency Injection: DI)
テスト実行スクリプトに対して、環境の操作能力を抽象化した **`WorkspaceEnvProtocol`**（`LocalWorkspaceEnv` サンドボックス）を外部から注入 (DI) する設計を採用します。

```mermaid
graph LR
    Evaluator[skill-evaluator] -->|1. Create Env| Env[LocalWorkspaceEnv (Git Sandbox)]
    Evaluator -->|2. Run Tests| Runner[ContractTestRunner / SimulationEvalRunner]
    Runner -->|3. Safe Interaction| Env
    Env -->|4. Safe Read/Write/Test| Files[(Virtual Filesystem)]
```

#### 1. OS直接操作の禁止と環境の抽象化
`skill-evaluator` は、内部で直接危険な OS 操作を行いません。すべてのファイル読み書きや単体テストの実行は、渡された `env` インスタンスを経由して行います。

#### 2. DI によるメリット
*   **環境の差し替え可能性 (Pluggability)**:
    テスト実行コードを変更することなく、実環境で実行する `RealWorkspaceEnv` や、テスト完了後に自動ロールバックを行う Git 管理下の `LocalWorkspaceEnv`（サンドボックス）を動的に切り替えられます。
*   **安全性の確保**:
    テスト実行中に発生したすべてのファイルの作成・変更・削除は仮想環境によって追跡され、実行後に完全にロールバックされるため、開発環境を汚さずに安全に何度でもテストを実行できます。
*   **標準ランナーの再利用 (Reusability)**:
    アサーション判定ロジックをゼロから実装せず、`edd-agent-tools.evaluation` パッケージ内の標準ランナー（`ContractTestRunner`, `SimulationEvalRunner` 等）に仮想環境 `env` を渡して実行を委譲します。

---

## 4. ドキュメント化の設計思想と関心の分離 (Documentation Design)

AIエージェント指向開発において、ドキュメントの陳腐化や情報の分散はハルシネーションの温床になります。本パッケージでは、ドキュメント化の関心を **「API仕様（個別・コード内）」** と **「システム制約（中央集権・Markdown）」** に完全に分離します。

```
                     ┌──────────────────────────────────────────────┐
                     │          Package (edd-agent-tools)           │
                     ├──────────────────────────────────────────────┤
                     │   [中央集権設計ドキュメント: AGENTS.md]     │
                     │   * システム全体のアーキテクチャ制約（How）  │
                     │   * 複数クラスにまたがる横断的ルール         │
                     └──────────────────────┬───────────────────────┘
                                             │ (参照 / ルールバインド)
                     ┌──────────────────────▼───────────────────────┐
                     │   [個別コード定義: Pydoc / Type hints]       │
                     │   * メソッド個別のAPI契約（What）            │
                     │   * 引数、戻り値の型、例外の定義             │
                     └──────────────────────────────────────────────┘
```

### 1. 個別API仕様 (What / How to Call) ➔ ソースコード内 (Pydoc)
個別のクラスやメソッドの使い方、引数の型、例外情報などは、**Pythonソースコード内の Docstring (Pydoc) および Type hints のみに記述** します。

### 2. 横断的システム制約 (How / Architecture Rules) ➔ パッケージ内 `AGENTS.md`
「DI（依存性注入）を用いて環境を渡す目的」「アサーションの合否判定で負例をどう扱うべきか」などの、**複数クラスにまたがる全体のアーキテクチャ制約や背景は、パッケージ同梱の `AGENTS.md`（または `test_architecture.md`）に集約して記述** します。
