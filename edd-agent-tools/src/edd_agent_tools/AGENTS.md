# edd-agent-tools 開発ルール (エージェント指向システム制約)

本ドキュメントは、`edd-agent-tools` パッケージを利用してスキルやテスト検証を自動実装するAIエージェントが遵守すべき **「厳密な開発制約 (System Rules)」** を定義します。

---

## 1. 単一真実源の原則と Progressive Disclosure 規約 (Markdown-First)
*   **単一真実源 (SSOT) ➔ `SKILL.md`**:
    スキルの仕様、トリガー条件、意思決定ツリー、ステップ手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化してください。`design.json` 等の中間設定ファイルは作成してはなりません。
*   **3層リソース分離**:
    - `scripts/`: 直接実行可能な決定論的スクリプト
    - `references/`: ドメイン知識・スキーマ・仕様書（オンデマンド参照用）
    - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
*   **ボイラープレートの排除**:
    多層ラッパー構造（`models.py`, `handler.py`, `nodes/`）を作成せず、フラットで簡潔な実装を行ってください。

---

## 2. 型仕様と Protocol の厳密遵守 (What/How)
テストの生成（Generator）および実行（Executor）のための新規スキルやコンポーネントを開発する際は、必ずパッケージ内に定義された Python `Protocol` 契約に適合させてください。

*   **参照クラス定義**: `edd_agent_tools.evaluation.models.TestGenerator`
*   **参照クラス定義**: `edd_agent_tools.evaluation.models.TestExecutor`

各クラスのシグネチャ、引数の名前、戻り値の型、発生すべき例外については、上記コード内の **Docstring および Type Hints** を唯一の真実のソースとして厳密に従ってください。

---

## 3. 依存性注入 (Dependency Injection) 制約 (What/How)
テストの実行器（Executor）は、自身の内部で OS やファイルシステムに直接アクセスしてはなりません。

*   **実行環境の操作制限**:
    必ず引数として注入される `env: WorkspaceEnvProtocol`（仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
    *   ファイルの作成・書き込み ➔ `env.step(WriteFileAction(...))`
    *   ファイルの表示・確認 ➔ `env.step(ViewFileAction(...))`
    *   テストコマンド (pytest) の実行 ➔ `env.step(RunPytestAction())`
*   **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能にするため。

---

## 4. テスト判定とアサーションの仕様 (What/How)

### A. 契約駆動テスト (Unitテスト)
*   **アサーションの委譲**:
    具象 Executor スキルはアサーションエンジンを独自に再実装せず、パッケージの **`edd_agent_tools.evaluation.ContractTestRunner`** に仮想環境 `env` を引き渡して実行を委譲してください。

### B. トリガー評価テスト (インテント判定)
*   **負例テストの合否アサーション**:
    対象スキルを「起動させてはならない」プロンプト（負例/Negativeケース）の検証時、LLMのインテント分類の予測が対象のスキル名と「不一致」だった場合は、誤起動を防げたことを意味するため、テストとしては **合格 (PASSED)** と判定してください。

---

## 5. コーディング規約と Pydoc (Docstring) の記述ルール (What/How)
1.  **Google Python Style Guide の厳密遵守**: すべての Python コードおよび Docstring は Google スタイル（`Args:`, `Returns:`, `Raises:`）に準拠してください。
2.  **個別API契約 (What/How) への特化**: Docstring には呼び出し仕様（引数型、戻り値、例外）のみを簡潔に記述し、設計思想（Why）は `docs/` 配下のドキュメントに集約してください。

---

## 6. プロンプトおよび仕様書の文体規約 (Imperative Form)
*   **動詞起点・客観的指示**: SKILL.md および指示プロンプトはすべて客観的な指示（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調や曖昧な助動詞（「〜してください」等）を排除してください。
*   **Frontmatter の description**: 第三者視点（"This skill should be used when..."）で、トリガー条件・対象ファイル・対応タスクを具体的に記述してください。

---

## 7. ドキュメント化の設計思想と各ファイルの役割分担 (What/How)
*   **`README.md`**: パッケージ全体の主要機能、インストール方法、CLI/MCP 使用例のみを記述。
*   **`src/edd_agent_tools/AGENTS.md`**: AIエージェント向けシステム制約のみを記述（本ドキュメント）。
*   **`src/edd_agent_tools/docs/`**: 設計思想やアーキテクチャ背景を集中配置。
