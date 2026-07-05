# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

> [!NOTE]
> 開発者向けの具体的な実装コード例や主要クラスのサンプルスニペットは、[docs/EXAMPLES.md](file:///workspace/edd-agent-tools/docs/EXAMPLES.md) を参照してください。

---

## 1. コア設計思想 (Core Design Philosophy)

本プロジェクトの実装および設計において、厳格に遵守すべき基本方針です。

*   **規約による設定 (Convention over Configuration)**:
    すべてのスキル・エージェントは統一されたファイル構成およびインターフェース規約（`scripts/handler.py`）に従います。これにより、型検証、CLIランナーの動的生成、インプロセス呼び出しが自動化されます。
*   **関心の分離 (Separation of Concerns)**:
    *   **薄いハンドラーとロジックの分離**: インターフェース定義を行う `handler.py` は自動生成されるため、手動編集は禁止です。実処理は `logic.py` 等に完全に分離します。
    *   **オブジェクト指向とモジュール分割 (単一責任の原則)**: コードの肥大化を防ぐため、役割に応じてモジュール（`client.py`, `parser.py` 等）を分割してください。
    *   **アセットの外部化**: プロンプト等はコード内に直書きせず、`assets/` ディレクトリに外部ファイル化し、`SkillDirectory` 経由でロードします。
*   **状態駆動・戻り値なし (State-Driven, Returnless)**:
    ビジネスロジック関数の戻り値は無視されます。結果は必ず `tool_context.state` に直接書き込んでください。
*   **コンテキストのクリーン化 (Clean Context)**:
    プロンプト内に巨大データを直接埋め込んで結合することを禁止します。ハルシネーションを防ぐため、`GeminiContentBuilder` で添付テキストパーツとして分離送信します。

---

## 2. スキルおよびエージェントの定義規約 (Convention)

### ① 統一ハンドラー規約 (`scripts/handler.py`)
エントリーポイントは `scripts/handler.py` に統一し、以下の3つを定義します。
1.  **`SKILL_METADATA`** (dict): 名前、説明、実行形式、出力モードなどの基本メタデータ。
2.  **`Input`** (Pydantic `BaseModel`): パラメータ検証スキーマ。
3.  **`process_message(tool_context: ToolContext)`**: `tool_context.state["validated_input"]` から検証済み引数を取り出し、ビジネスロジックを呼び出す。

### ② ビジネスロジック実装規約 (`scripts/logic.py`)
*   パラメータの取得および処理結果の保存は、すべて `tool_context.state` に対し直接行います。

---

## 3. 主要クラスの役割

*   **`SkillDirectory` / `SkillRegistry`**:
    スキルのルート、アセット、ソースコードパスの自動解決。およびプロンプトなどのアセットファイルの安全ロード。
*   **`GeminiContentBuilder`**:
    指示プロンプトとソースコード等の添付データを分離し、LLM送信用のマルチパーツ（Gemini Content）を構築。
*   **`LibraryDocumentationReader`**:
    本ドキュメント（README.md）を動的にロードし、LLMのシステムプロンプト等に開発規約として添付可能にする。

---

## 4. 日本語テスト実行パッチ (Monkey Patch)
ADK 2.0 評価器（Rouge-1）の日本語文字分割問題を解決するため、`bert-base-multilingual-cased` による多言語トークナイズパッチを `adk eval` 実行時に自動適用します。
