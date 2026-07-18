# edd-agent-tools 開発ルール (エージェント指向システム制約)

本ドキュメントは、`edd-agent-tools` パッケージを利用してスキルやテスト検証を自動実装するAIエージェントが遵守すべき **「厳密な開発制約 (System Rules)」** を定義します。

---

## 1. 型仕様と Protocol の厳密遵守 (What/How)
テストの生成（Generator）および実行（Executor）のための新規スキルやコンポーネントを開発する際は、必ずパッケージ内に定義された以下の Python `Protocol` 契約に適合させてください。

*   **参照クラス定義**: `edd_agent_tools.evaluation.models.TestGenerator`
*   **参照クラス定義**: `edd_agent_tools.evaluation.models.TestExecutor`

各クラスのシグネチャ、引数の名前、戻り値の型、発生すべき例外については、上記コード内の **Pydoc (Docstring) および Type Hints** を唯一の真実のソース (Single Source of Truth) として厳密に従ってください。

---

## 2. 依存性注入 (Dependency Injection) 制約 (What/How)
テストの実行器（Executor）は、自身の内部で OS やファイルシステムに直接アクセスしてはなりません。

*   **実行環境の操作制限**:
    必ず引数として注入される `env: WorkspaceEnvProtocol`（Gymnasium 形式の仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
    *   ファイルの作成・書き込み ➔ `env.step(WriteFileAction(...))`
    *   ファイルの表示・確認 ➔ `env.step(ViewFileAction(...))`
    *   テストコマンド (pytest) の実行 ➔ `env.step(RunPytestAction())`
*   **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能（ロールバック可能）にするため。

---

## 3. テスト判定とアサーションの仕様 (What/How)

### A. スキーマ駆動テスト (Unitテスト)
*   **アサーションの委譲**:
    具象 Executor スキルはアサーションエンジンを独自にゼロから再実装（車輪の再発明）せず、パッケージで提供されている **`edd_agent_tools.evaluation.SchemaDrivenTestRunner`** をインポートし、これに仮想環境 `env` を引き渡して実行を委譲してください。

### B. トリガー評価テスト (インテント判定)
*   **負例テストの合否アサーション**:
    対象スキルを「起動させてはならない」プロンプト（負例/Negativeケース）の検証時、LLMのインテント分類の予測が対象のスキル名と「不一致」だった場合は、誤起動を防げたことを意味するため、テストとしては **合格 (PASSED)** と判定してください。対象スキルを誤って起動してしまった（一致してしまった）場合のみ不合格（FAILED）とします。

---

## 4. 設計思想と背景の参照先
本システム全体の Generator-Executor ペアリングパターンの目的、プラグイン型ディスパッチの有向グラフ設計思想、背景、ダイアグラムについては、必要に応じて以下のドキュメントを自律的にロード（遅延参照）して確認してください。

*   **設計ドキュメントパス**: `edd-agent-tools/docs/test_architecture.md`

---

## 5. コーディング規約と Pydoc (Docstring) の記述ルール (What/How)
AIエージェント自身が新規コード（スキル、クラス、ヘルパー等）を実装または修正する際は、以下のドキュメント化ルールを厳密に遵守してください。

1.  **Google Python Style Guide の厳密遵守**:
    すべての Python コードおよび Docstring は、Google スタイル（`Args:`, `Returns:`, `Raises:`）に準拠して記述してください。
2.  **個別API契約 (What/How) への特化**:
    コード内の Docstring には、その関数やクラスの「呼び出し仕様（引数の型と意味、戻り値、発生しうる例外）」のみを簡潔に記述してください。
3.  **背景や思想 (Why) のインライン記述の禁止**:
    Docstring 内に「なぜこの設計にしたか」「システム全体のアーキテクチャの背景」といった設計思想（Why）を記述することを禁止します。これらはすべて `docs/` 配下の中央ドキュメントに集約し、ソースコードは型とAPI仕様だけを語るクリーンな状態に保ってください。

