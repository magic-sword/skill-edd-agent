# skill-coder 設計思想 (Design Philosophy)

このドキュメントは、`skill-coder` および ADK 2.0 スキル開発におけるコアな設計思想、アーキテクチャの原則、および AI（SkillDeveloperAgent）へ向けたコーディングのガイダンスをまとめたリファレンスです。

---

## 1. オブジェクト指向設計 (OOP) と `SkillExecutor` の強制

手続き的な平坦コード（スクリプトベタ書き）を根絶し、責務ごとに分割された堅牢なオブジェクト指向設計を強制するため、スキルの中心的なエントリーポイントとして **`SkillExecutor`** クラスを導入しています。

* **ハンドラーの薄肉化**:
  自動生成される [scripts/handler.py](file:///workspace/src/skills/skill-coder/scripts/handler.py) は、インプロセスロードのゲートウェイ（窓口）に徹し、ビジネスロジック自体は `from .executor import SkillExecutor` からインスタンスを生成して `.execute()` を呼ぶだけの最小構成とします。
* **LLMへのプライミング効果**:
  プレースホルダーである [executor.py.template](file:///workspace/src/skills/skill-coder/assets/executor.py.template) に `class SkillExecutor` の骨組みを定義しておくことで、これを読み込んだ AI（SkillDeveloperAgent）に対し、「この executor を中心として、責務に応じたプライベートクラスやモジュール（APIクライアント, プロンプター等）へ適切に分割・カプセル化して実装しなさい」というオブジェクト指向設計への強力なプライミング（先行刺激）を与えます。

---

## 2. 仕様概要（What）と追加要望（How）の分離マージ

設計書ファイル（`design.json`）に記録される静的な情報と、実行時に人間から与えられる動的な指示を、役割（意味論）に応じて明確に分離し、LLM へと安全に伝達します。

1. **仕様概要 (`summary`) [What]**:
   * そのスキルの本質的なビジネス目的や本来あるべき役割・仕様を、`design.json` の `summary` フィールドに静的に記録・永続化します。
   * これにより、既存コード改修時に「コードから仕様概要をLLMに毎回推論させる（非決定論的ブレが生じる）」ことを防ぎ、一貫した基本仕様（What）を静的マスターデータとして提供します。
2. **実装の追加要望 (`prompt`) [How]**:
   * コマンド引数として動的に渡される `--prompt` は、既存設計に対する「差分改修のこだわり」や「今回の具体的な実装指示」として扱います。
3. **エグゼキューター内でのマージ**:
   * `SkillExecutor` 内部で、静的概要（What）と動的要望（How）を以下のように区分けして結合し、LLMにインプットとして引き渡します。
     ```python
     full_prompt = f"=== 基本仕様概要（What） ===\n{design_data.summary}\n\n=== 今回の実装・改修要望（How） ===\n{prompt}"
     ```

---

## 3. 入力（Input）および出力（Output）スキーマの定義思想

外部インターフェースとのやり取りにおける型安全性と構造化データの対称性を保証するため、すべてのデータ定義には Pydantic (V2) を採用し、厳格なバリデーションモデルを実装します。

* **入力モデル（`Input`）の型安全**:
  * 外部（フレームワークやCLI）から渡されるパラメータはすべて `Input` クラスとしてパース・バリデーションされます。これによって型エラーや不足パラメータがビジネスロジックへ侵入するのを水際で防ぎます。
* **出力モデル（`Output`）による構造化応答**:
  * ロジックの処理結果は、単なるプレーンテキストや不定形な辞書ではなく、必ず `Output` クラスのインスタンスとしてカプセル化します。
  * これにより、戻り値に「どのようなキー（status, message, 生成ファイル一覧など）が含まれているか」が完全に型として明示され、呼び出し側の親LLMがプログラムとして処理結果を安全かつ確実に解釈・パースすることを保証します。
* **`VALUE_ONLY` または `CONVERSATIONAL` における `Output` の定義**:
  * 出力モードが `VALUE_ONLY` や `CONVERSATIONAL` である場合でも、ビジネスロジック内では一貫して `Output` モデルの返却が要求されます。
  * この場合、`Output` クラスのスキーマ定義の中に、返却したいプレーンテキストの値を格納するための **`value`** フィールド（型: `str`）を必ず定義してください。
    ```python
    class Output(BaseModel):
        value: str = Field(..., description="返却するメインテキストの値。")
    ```
  * `handler.py` の `process_message` が、戻り値のインスタンスからこの `value` 属性のテキストを自動的にアンラップして文字列として返します。

---

## 4. `process_message` の役割と出力モード（`OutputMode`）の制御

[scripts/handler.py](file:///workspace/src/skills/skill-coder/scripts/handler.py#L13-L21) に自動生成される `process_message(params: Input, tool_context: ToolContext) -> str` は、インプロセスロード時における共通のエントリーポイントとして、ビジネスロジックと実行環境（ADKフレームワーク）を仲介する決定論的なアダプターです。

* **薄い中継機能**:
  * 関数内部では一切のビジネスロジックを持たず、渡された `Input` と `ToolContext` をそのまま `SkillExecutor` に引き渡して処理をキックします。
* **出力モード（`OutputMode`）の自動シリアライズ制御**:
  * `SkillExecutor.execute()` が返した `Output` インスタンスに対し、スキルの設計で規定されている `output_mode` に従って、戻り値の文字列形式を自動的に型変換（シリアライズ）します。
    1. **`VALUE_ONLY` または `CONVERSATIONAL`**:
       * ユーザーとのチャットや直接の値参照を目的としているため、`Output` の持つ主要なテキスト値（`result.value`）に自動アンラップし、純粋なプレーンテキスト文字列として呼び出し側に返します。
    2. **`STRUCTURED_JSON`**:
       * 他のツールやプログラムが機械的にパースすることを想定しているため、`result.model_dump_json(by_alias=True)` を実行し、厳格なJSONスキーマに準拠したJSON文字列としてシリアライズして返します。

---

## 5. カプセル化と公開APIの最小化

ライブラリ共通規約（カプセル化の原則）に基づき、スキルのパブリックAPI（パッケージの外部へ露出される公開インターフェース）は、自動生成される `__init__.py` の以下の4つの要素に厳格に制限されます。

* `process_message` (インプロセスロード用関数)
* `SKILL_METADATA` (スキル名、説明などのメタ辞書)
* `Input` (Pydantic 入力スキーマ)
* `Output` (Pydantic 出力スキーマ)

これら以外の、開発者が自律的に設計・作成するモジュール（例: `scripts/client.py`, `scripts/prompter.py` など）や `SkillExecutor` 自身は、パッケージ内部の実装詳細（プライベート）としてカプセル化し、決して外部へエクスポートしてはなりません。

---

## 6. ブートストラップロードの安全性の担保

スキルの初期ロード時（AIエージェントによる自動生成が始まる前の、`executor.py` などのAI生成ファイルがディスクにまだ存在しない初期化フェーズ）においても、`handler.py` がインポートエラーでクラッシュすることを完全に防ぐ「ブートストラップロードの安全性」を担保します。

* `__init__.py.template` には、まだ存在しない可能性のある `executor.py` からのインポート（`from .executor import SkillExecutor` など）を**絶対に含めない**ようにします。
* `handler.py` は、インプロセス起動時（`process_message` が呼び出される時）に初めて `executor` モジュールをロードし、`SkillExecutor` をキックするように動作します。
