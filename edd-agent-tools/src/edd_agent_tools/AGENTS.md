# edd-agent-tools 開発ルール (エージェント指向システム制約 / SSOT)

本ドキュメントは、`edd-agent-tools` パッケージを利用してスキル開発・自律改善・評価検証を実装するAIエージェントが遵守すべき **「厳密な開発制約 (System Rules)」** の単一真実源（Single Source of Truth）です。

---

## 1. パッケージとスキルの責務分離 (Two-Tier Architecture & Loose Coupling)
*   **基盤パッケージ (`edd-agent-tools`) の責務**:
    - 統合 CLI `edd`（動的ディスパッチ `edd run <skill>`, `edd init`, `edd validate`, `edd package`, `edd eval`, `edd tier-gate`, `edd diagnose`）を提供する。
    - スキルの探索・パス解決（`SkillsState`, `Skill`）、仮想環境サンドボックス（`LocalWorkspaceEnv`）、多層評価・Tier昇格テスト（`ContractTestRunner`, `SimulationEvalRunner`）、静的バリデーション（`SkillValidator`）、Google ADK 2.0 `EddSkillToolset` / MCP 連携等の共通基盤ロジックを一元管理する。
*   **スキル (`src/skills/`) の責務**:
    - `SKILL.md`（意思決定ツリー・手順書）、`references/`（ドメイン知識）、`assets/`（テンプレート）、`scripts/`（業務スクリプト）に特化する。
    - **完全な自己完結性（Portability / Zero-dependency）**: スキル内のスクリプトは外部パッケージ `edd_agent_tools` を直接 Python import してはならない。Python 標準ライブラリのみで実装するか、統合 CLI `edd` を subprocess 呼び出しする設計とする。
    - **二重 LLM 呼び出しの禁止（Anti-pattern）**: スキル内のスクリプト内部で直接 LLM API を叩くバッチ処理を抱え込まず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計とする。スクリプトは決定論的なブラックボックス CLI ツール（`argparse` / `--help` 対応）として実装する。

---

## 2. 単一真実源の原則と Progressive Disclosure 規約 (Markdown-First)
*   **単一真実源 (SSOT) ➔ `SKILL.md`**:
    スキルの仕様、トリガー条件、意思決定ツリー、ステップ手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化する。
*   **3層リソース分離**:
    - `scripts/`: 直接実行可能な決定論的スクリプト（CLI対応）
    - `references/`: ドメイン知識・スキーマ・仕様書（オンデマンド参照用）
    - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
*   **ボイラープレートの排除**:
    多層ラッパー構造（`models.py`, `handler.py`, `nodes/`）を作成せず、フラットで簡潔な実装を行う。

---

## 3. 型仕様とドメインモデルの厳密遵守 (What/How)
スキル操作・構文解析・テスト実行を行う新規機能やスクリプトを開発する際は、必ずパッケージ内に定義されたドメインモデルおよび評価ランナーに適合させてください。

*   **スキル管理モデル**: `edd_agent_tools.skills.Skill`, `edd_agent_tools.skills.SkillSpec`, `edd_agent_tools.skills.SkillsState`
*   **品質保証モデル**: `edd_agent_tools.skills.SkillLogicDraft`, `edd_agent_tools.skills.SkillValidator`
*   **自動生成エンジン**: `edd_agent_tools.skills.SkillCreationEngine`, `edd_agent_tools.evaluation.EvalSetGenerator`
*   **評価実行基盤**: `edd_agent_tools.evaluation.ContractTestRunner`, `edd_agent_tools.evaluation.SimulationEvalRunner`

各クラスのシグネチャ、引数の名前、戻り値の型、発生すべき例外については、上記コード内の **Docstring および Type Hints** を唯一の真実のソースとして厳密に従ってください。

---

## 4. 依存性注入 (Dependency Injection) 制約 (What/How)
テスト実行や安全な試行錯誤を行うスクリプトは、自身の内部で OS や実ファイルシステムに直接アクセスしてはなりません。

*   **実行環境の操作制限**:
    必ず引数として注入される `env: WorkspaceEnvProtocol`（`LocalWorkspaceEnv` 等の仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
    *   ファイルの作成・書き込み ➔ `env.step(WriteFileAction(...))`
    *   ファイルの表示・確認 ➔ `env.step(ViewFileAction(...))`
    *   テストコマンド (pytest) の実行 ➔ `env.step(RunPytestAction())`
*   **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能にするため。

---

## 5. 自動生成物に対する品質ハーネス (Quality Gates)
スキルの新規生成や改修時は、必ず以下の4段階品質保証パイプラインを遵守する：
1. **Stage 1 (Logical Extraction)**: `SkillLogicDraft` による論理設計抽出
2. **Stage 2 (Deterministic Rendering)**: `SkillTemplateEngine` による決定論的 SKILL.md レンダリング
3. **Stage 3 (Static Linter)**: `SkillValidator`（または `quick_validate.py`）による静的リンター（構文・実在整合性・文字数制約）の 100% 合格
4. **Stage 4 (Contract Verification)**: `ContractTestRunner` による初期契約テスト検証

---

## 6. プロンプトおよび仕様書の文体規約 (Imperative Form)
*   **動詞起点・客観的指示**: SKILL.md および指示プロンプトはすべて客観的な指示（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調や曖昧な助動詞（「〜してください」等）を排除してください。
*   **Frontmatter の description**: 第三者視点（"This skill should be used when..."）で、トリガー条件・対象ファイル・対応タスクを100 words以内で極めて具体的に記述してください。

---

## 7. ドキュメント化の設計思想と各ファイルの役割分担 (What/How)
*   **`README.md`**: パッケージ全体の主要機能、インストール方法、CLI/MCP 使用例のみを記述。
*   **`src/edd_agent_tools/AGENTS.md`**: AIエージェント向けシステム制約のみを記述（本ドキュメント）。
*   **`src/edd_agent_tools/docs/`**: 設計思想やアーキテクチャ背景を集中配置。
