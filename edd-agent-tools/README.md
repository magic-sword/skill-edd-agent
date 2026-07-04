# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

---

## 1. コア設計思想 (Core Design Philosophy)

本プロジェクトおよび `edd-agent-tools` は、以下の設計思想に則って開発されています。人間およびAIエージェントは、コードの実装・設計時にこれらの思想を厳格に遵守しなければなりません。

### ① 規約による設定 (Convention over Configuration)
すべてのスキル/エージェントは、あらかじめ定義されたファイル構成およびインターフェース規約（後述の `scripts/handler.py`）に従う必要があります。規約に従うことで、型バリデーション、CLIランナーの動的引数生成、安全なインプロセス呼び出しが自動的に動作します。

### ② 関心の分離 (Separation of Concerns)
* **薄いハンドラーとロジックの分離**: インターフェース定義を行うハンドラー（`handler.py`）は薄く保ち、実処理は `logic.py` 等の別ファイルに分離します。ハンドラーは設計図から自動生成されるため、手動編集は禁止です。
* **オブジェクト指向とモジュール分割 (単一責任の原則)**: 1つのファイルにすべてのロジックを詰め込む（肥大化させる）ことを禁止します。外部API通信は `client.py`、データのパースは `parser.py` など、役割に応じてモジュールを分割してください。
* **アセットの外部化**: プロンプトテンプレートや巨大な設定データは、Pythonコード内に文字列リテラルとして直書きせず、`assets/` ディレクトリに外部ファイルとして抽出し、`SkillDirectory` 経由でロードします。

### ③ 状態駆動・戻り値なし (State-Driven, Returnless)
ビジネスロジック関数の戻り値（`return`）は通常無視されます。結果は必ず `tool_context.state["キー名"] = 値` または `tool_context.state.update(結果辞書)` を使用して、**`ToolContext.state` に直接書き戻してください**。

### ④ コンテキストのクリーン化 (Clean Context)
プロンプト指示の文字列内に、ソースコードやCSVなどの別データを直接埋め込んで結合することを禁止します。ハルシネーションとコンテキスト汚染を防ぐため、`GeminiContentBuilder` を使用して、指示とは独立した「添付テキストパーツ」として送信します。

---

## 2. スキルおよびエージェントの定義規約 (Convention)

### ① 統一ハンドラー規約 (`scripts/handler.py`)
すべてのスキル・エージェントは、エントリーポイントを `scripts/handler.py` に統一します。このファイルには以下の3つを定義します。

1. **`SKILL_METADATA`** (dict): 基本メタデータ（名前、説明、実行形式、出力モード等）。
2. **`Input`** (Pydantic `BaseModel`): 要求引数を定義したスキーマ（型ヒント、説明文含む）。
3. **`process_message(tool_context: ToolContext)`** (func): エントリーポイント。型検証済みの引数 `tool_context.state["validated_input"]` を受け取ります。

#### 実装例 (`scripts/handler.py` - 薄いハンドラー)
```python
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic # 相対インポートを推奨

SKILL_METADATA = {
    "name": "my-sample-skill",
    "description": "サンプルスキルの説明。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON"
}

class Input(BaseModel):
    city: str = Field(..., description="対象都市の名前")

def process_message(tool_context: ToolContext):
    # 1. バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 2. 引数を state に移行
    if params:
        for key, value in params.model_dump().items():
            if value is not None:
                tool_context.state[key] = value
                
    # 3. ビジネスロジックを呼び出す
    run_logic(tool_context)
```

### ② ビジネスロジック実装規約 (`scripts/logic.py`)
ビジネスロジックは、必ず以下のように実装します。
* `ToolContext` は必ず `from google.adk.tools import ToolContext` からインポートします（非公式のインポート元は使用不可）。
* パラメータは `tool_context.state` から取得し、結果も直接 `tool_context.state` に書き戻します。

#### 実装例 (`scripts/logic.py` - ロジックの実体)
```python
from google.adk.tools import ToolContext
from .client import WeatherClient # 分割されたモジュール

def process_message(tool_context: ToolContext):
    city = tool_context.state.get("city")
    if not city:
        raise ValueError("city is required")
        
    client = WeatherClient()
    temp_c, temp_f = client.fetch_temp(city)
    
    # 結果は必ず state に直接書き込む (戻り値を return しない)
    tool_context.state["celsius"] = temp_c
    tool_context.state["fahrenheit"] = temp_f
```

---

## 3. 主要モジュールの使用方法

### ① `SkillDirectory` (パス解決とアセットロード)
パスの解決やプロンプトファイルの読み込みを手続き的に記述せず、このクラスにカプセル化します。
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
directory = registry.get_skill_directory(name="skill-spec-writer")

# 主要パスへのアクセス (os.path.joinのハードコード全廃)
design_path = directory.design_path         # assets/design.json の絶対パス
source_code_dir = directory.source_code_dir # scripts/ の絶対パス

# アセットファイル（プロンプト等）の安全ロード (open処理の全廃)
prompt_content = directory.load_asset("prompt.txt")
```

### ② `GeminiContentBuilder` (マルチパーツ送信)
ソースコード等の添付データを指示プロンプトから分離し、独立したパーツとして構築します。
```python
from edd_agent_tools.gemini import GeminiContentBuilder

builder = GeminiContentBuilder("指示プロンプト...")
# 指定ディレクトリのPythonファイルを添付パーツとして追加
builder.add_dir(
    directory="/workspace/src/skills/my-skill/scripts",
    ref_root="/workspace/src/skills/my-skill",
    file_filter=lambda path: path.endswith(".py")
)
# generate_content に渡すマルチパーツのリストを取得
contents = builder.build()
```

### ③ `SkillRegistry` (インプロセス解決)
同一プロセス内で複数のスキルを順次ロードする際、相対インポートの名前空間衝突を回避して動的にインポートします。
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
# 相対インポートの競合なく、安全にハンドラーモジュールをロード
handler_module = registry.load_handler("my-sample-skill")
```

---

## 4. 日本語テスト実行パッチ (Monkey Patch)
ADK 2.0 のデフォルト評価器（Rouge-1）はスペース区切り前提のため、日本語でテストすり抜けバグが発生します。
本パッケージは、`adk eval` の実行時に自動的に `PYTHONPATH` にパッチを差し込み、`rouge_score` のトークナイザーを多言語モデル（`bert-base-multilingual-cased`）に差し替えることで、日本語の評価精度を担保します。

---

## 5. パッケージ共通化処理一覧 (Summary of Shared Processes)

本パッケージ `edd-agent-tools` で共通化されている主要な処理は以下の通りです。

*   **パス・ディレクトリ管理 (`SkillDirectory` / `SkillRegistry`)**
    *   スキルのルート、アセット、ソースコードパスの自動解決。
    *   テスト用の評価データ（`.evalset.json`、`.evalset.config.json`）の規定フォルダへの一貫した保存。
*   **LLM送信の最適化 (`GeminiContentBuilder`)**
    *   指示プロンプトとソースコード、各種ドキュメント等の添付テキストを分離し、マルチパーツ（Gemini Content）として構成する処理。
*   **Gemini API クライアント初期化 (`get_gemini_client`)**
    *   環境変数 `GEMINI_API_KEY` の設定に基づき、`google-genai` 互換クライアントを簡潔に初期化。
*   **Pydanticスキーマ調整 (`remove_additional_properties`)**
    *   Gemini APIの構造化出力（`response_schema`）でエラーの原因となる `additionalProperties: false` 属性などをスキーマ定義から自動除去する処理。
*   **日本語ROUGE評価の正常化（多言語対応パッチ）**
    *   ADK標準評価器の日本語文字分割問題を解決するため、`bert-base-multilingual-cased` による多言語トークナイズパッチを適用。
*   **ドキュメント読込 (`LibraryDocumentationReader`)**
    *   プロジェクト内の共通規約やドキュメントを読み出し、LLMのコンテキストとして動的に添付可能にする処理。
