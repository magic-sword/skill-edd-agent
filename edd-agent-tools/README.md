# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

> [!NOTE]
> 開発者向けの具体的な実装コード例や主要クラスのサンプルスニペットは、[docs/EXAMPLES.md](file:///workspace/edd-agent-tools/docs/EXAMPLES.md) を参照してください。

---

## 1. コア設計思想 (Core Design Philosophy)

本プロジェクトの実装および設計において、厳格に遵守すべき基本方針です。

*   **規約による設定 (Convention over Configuration)**:
    すべてのスキル・エージェントは統一されたファイル構成およびインターフェース規約に従います。動的インプロセスロードの窓口は `scripts/__init__.py` に統一され、これにより型検証、CLIランナーの動的生成、インプロセス呼び出しが自動化されます。
*   **関心の分離 (Separation of Concerns)**:
    *   **薄いハンドラーとロジックの分離**: エントリポイントとなる `scripts/__init__.py` および `handler.py` は自動生成されるため、手動編集は禁止です。実処理は `logic.py` 等に完全に分離します。
    *   **オブジェクト指向とモジュール分割 (単一責任の原則)**: コードの肥大化を防ぐため、役割に応じてモジュール（`client.py`, `parser.py` 等）を分割してください。
    *   **アセットの外部化**: プロンプト等はコード内に直書きせず、`assets/` ディレクトリに外部ファイル化し、`Skill` クラス経由でロードします。
*   **明示的な入力とテキストフィードバック (Explicit Input & Text Feedback)**:
    パラメータの受け渡しは Pydantic モデルを用いて関数の引数レベルで明示的に行います。また、AIツールとしての実行成否や実行結果のサマリーは関数の戻り値（`str`）として返してください。
*   **コンテキストのクリーン化 (Clean Context)**:
    プロンプト内に巨大データを直接埋め込んで結合することを禁止します。ハルシネーションを防ぐため、`GeminiContentBuilder` で添付テキストパーツとして分離送信します。

---

## 2. スキルおよびエージェントの定義規約 (Convention)

### ① 統一エントリーポイント規約 (`scripts/__init__.py`)
Entrypoint to load dynamically in-process is `scripts/__init__.py`, from which the following 3 elements are re-exported (exposed):
1.  **`SKILL_METADATA`** (dict): 名前、説明、実行形式、出力モードなどの基本メタデータ。
2.  **`Input`** (Pydantic `BaseModel`): パラメータ検証スキーマ。
3.  **`process_message(params: Input, tool_context: ToolContext) -> str`**: 第1引数に `Input` インスタンスを受け取り、第2引数に `ToolContext` を受け取ります。戻り値として実行結果のサマリー（str）を返します。

### ② ビジネスロジック実装規約 (`scripts/logic.py`)
*   パラメータの取得は第1引数 `params` から行います。実行結果の永続化等は `tool_context.state` に対し行いますが、完了のサマリーメッセージは戻り値（str）として返します。

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

---

## 3. 主要クラスの役割

*   **`Skill` / `SkillRegistry`**:
    スキルのルート、アセット、ソースコードパスの自動解決、インプロセス動的ロード（`load_module()`）、FunctionToolオブジェクトの生成。およびプロンプトなどのアセットファイルの安全ロード。
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

## 5. 前提条件と動作環境 (Prerequisites)

本ライブラリは、Pydanticモデルの `StrEnum` などの機能を使用しているため、以下の環境が必要です。
*   **Python**: `>= 3.11` (Python 3.11 以上を必須とします)

