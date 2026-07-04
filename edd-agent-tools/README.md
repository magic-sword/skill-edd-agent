# edd-agent-tools

EDD（評価駆動開発）によるAIエージェント開発をサポートするための共通ツールおよびヘルパーライブラリ。

## 主な機能

* **共通CLIランナー (`edd_agent_tools.cli.run`)**: 
  各スキルの `Input`（Pydanticモデル）から引数を自動的に構築し、型検証および実行結果の保存までを制御する統合CLIエントリーポイント。
* **スキルレジストリ (`edd_agent_tools.registry.SkillRegistry`)**:
  プロジェクト内のスキル/エージェントを `skills_registry.json` にベースに動的に検索・ロード・カプセル化するモジュール。
* **スキルディレクトリモデル (`edd_agent_tools.registry.SkillDirectory`)**:
  特定のスキルのフォルダ構造と各主要ファイルのパスを一元管理し、`load_asset` によるプロンプト等のロード処理をカプセル化するドメインモデル。
* **モックコンテキスト (`edd_agent_tools.testing.mock_context`)**:
  テスト・デバッグ用の `MockInvocationContext` を提供。
* **Geminiコンテンツビルダー (`edd_agent_tools.gemini.GeminiContentBuilder`)**:
  Gemini APIへのソースコードやアセット等のマルチパーツ添付を管理し、プロンプト直書きによるコンテキスト汚染を防ぐ支援ツール。

---

## スキルおよびエージェントの定義規約 (Entrypoint Convention)

`edd-agent-tools` は、**「規約による設定 (Convention over Configuration)」** に基づいて設計されています。すべてのスキルおよびエージェントは、以下のインターフェース規約に完全に従って定義されます。

### 1. 統一ハンドラー規約 (`scripts/handler.py`)
すべてのスキル・エージェントは、動的ロードのエントリーポイントとして常に **`scripts/handler.py`** を配備しなければなりません。この中には以下の3つの要素を定義します。

* **`SKILL_METADATA`** (辞書): 
  スキルの基本メタデータ（名前、説明、実行形式、出力モード等）。
* **`Input`** (Pydantic `BaseModel`): 
  スキルが要求する引数（型、必須/任意、説明文）を定義したスキーマ。
* **`process_message(tool_context: ToolContext)`** (関数): 
  スキルのメインビジネスロジック。バリデーション済みの入力パラメータ（`tool_context.state["validated_input"]`）を受け取って処理を実行します。

#### 定義例 (`scripts/handler.py`)
```python
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext

SKILL_METADATA = {
    "name": "my-sample-skill",
    "description": "サンプルスキルの説明。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON"
}

class Input(BaseModel):
    requirement: str = Field(..., description="指示テキスト。")
    output_dir: str = Field(..., description="出力先ディレクトリ。")

def process_message(tool_context: ToolContext):
    # バリデーション済みのPydanticオブジェクトを安全に取得
    params: Input = tool_context.state.get("validated_input")
    
    # ビジネスロジックの実行
    print(f"Processing: {params.requirement} -> {params.output_dir}")
```

---

## 設計思想と動的インポート解決

### 1. インプロセス呼び出しにおけるキャッシュ干渉の完全解消
同一プロセス内で異なる複数のスキルを順次ロードして実行（例: `eval-unit-tester` によるテスト生成や `test-executor` によるテスト実行）する際、通常の Python インポートシステムでは `"scripts.handler"` などのパッケージ名が競合し、モジュールが互いに上書きされてしまう問題（キャッシュ干渉）が発生します。

これを解消するため、`SkillRegistry.load_handler(skill_name)` は以下の**ベストプラクティス**に沿ってロードをカプセル化しています。

* **一意の名前空間への仮想マッピング**:
  ロード時に、モジュール名を `edd_agent_tools.dynamic_skills.{skill_name}.scripts.handler` のように一意に名前空間化します。
* **ダミーパッケージの登録による相対インポートの動作保証**:
  `sys.modules` に対象スキルの仮想的なパッケージ階層を動的に組み立てて登録します。これにより、インプロセスでの動的インポート時にも、`handler.py` 内に記述されたローカル相対インポート（例: `from .xxx import yyy`）が競合することなく標準の仕組み通り正常に解決されます。
* **`sys.modules` を破壊しない**:
  モジュールを `del` するなどの危険なランタイムハックを一切排除し、安全にモジュール空間を分離しています。

#### 呼び出し方法
```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()
# キャッシュの競合なく、相対インポートも動作する状態で安全にモジュールをロード
handler_module = registry.load_handler("my-sample-skill")
```

### 2. 共通CLIランナーによるスキーマ駆動実行 (Schema-Driven CLI)
共通CLIランナー (`edd-run` / `edd_agent_tools.cli.run`) は、指定されたスキルの `Input` クラスからコマンドライン引数を自動生成してパースし、型検証を行ってからビジネスロジックを実行します。

* **重複回避**: スキーマ内に共通引数（`--skill_name` 等）と同じフィールドがあっても、argparse の衝突エラーを自動回避します。
* **エスケープ対策**: 説明文に `%` (パーセント記号) が含まれる場合でも、argparse のフォーマットパースエラーが発生しないように自動的にエスケープを行います。

#### 実行方法
```bash
# 共通ランナー経由で特定のスキルを実行する
PYTHONPATH=/workspace/edd-agent-tools/src python3 -m edd_agent_tools.cli.run \
  --skill_name my-sample-skill \
  --requirement "新しい仕様の設計" \
  --output_dir "/tmp/my_output"
```

### 3. オブジェクト指向パス解決とアセットロード (SkillDirectory)
パス解決やアセットファイル（`prompt.txt`等）のロード処理が手続き的に散らばるのを防ぐため、スキルのディレクトリ構造とファイルの知識はすべて `SkillDirectory` クラスにカプセル化されます。
`SkillRegistry` は、`name` または `design_path` のいずれかから解決された `SkillDirectory` オブジェクトを構築して返すファクトリとして機能します。

```python
from edd_agent_tools.registry import SkillRegistry

registry = SkillRegistry()

# スキル名、またはdesign_pathから、対応するSkillDirectoryオブジェクトを一元特定
directory = registry.get_skill_directory(name="skill-spec-writer")

# フォルダ構造の主要パスへのアクセス (os.path.joinのハードコード全廃)
design_path = directory.design_path         # .../assets/design.json
source_code_dir = directory.source_code_dir # .../scripts
spec_path = directory.spec_path             # .../SKILL.md

# アセットファイル（プロンプトなど）の安全なロード (open処理の全廃)
prompt_content = directory.load_asset("prompt.txt")
```

### 4. コンテキスト汚染を防ぐマルチパーツ添付 (GeminiContentBuilder)
ソースコード全体をプロンプト指示の文字列内に直接埋め込む（結合する）と、プロンプトが巨大化してコンテキスト汚染を招き、ハルシネーションが発生しやすくなります。
`GeminiContentBuilder` を使用することで、指示プロンプトとは分離された独立した「添付テキストパーツ」として各ファイルをGemini APIに送信できます。
また、任意のファイルを判定・抽出するための「フィルタ用デリゲート（`Callable` コールバック）」をサポートしています。

```python
from edd_agent_tools.gemini import GeminiContentBuilder

# メインの指示プロンプトでビルダーを初期化
builder = GeminiContentBuilder("設計要件: ...")

# フィルタデリゲートを指定し、Pythonソースコード（.py）のみを個別の添付ファイルとして追加
builder.add_dir(
    directory="/workspace/src/skills/my-skill/scripts",
    ref_root="/workspace/src/skills/my-skill",
    file_filter=lambda path: path.endswith(".py")
)

# Gemini APIの generate_content にそのまま渡せるマルチパーツ（list[str]）を取得
contents = builder.build()
```

---

## 多言語（日本語）テスト実行パッチについて

### 背景と目的
ADK 2.0 が標準で利用している Rouge-1 評価器（`final_response_match_v1`）は、内部でスペース区切り（英語向け）のトークナイザーを使用しているため、日本語のようなスペース区切りのない言語では、テキスト全体が巨大な1トークン扱いとなり、曖昧なマッチングによって「不合格のケースが合格として判定されてしまう（すり抜け）」というバグが発生します。

### 仕組み（Monkey Patch のインジェクション）
Python の自動フックファイルである `usercustomize.py` をパッケージ内の `patch/` ディレクトリ配下に定義しています。
`test-executor` 内から `adk eval` をサブプロセスとして実行する際、このパッチディレクトリが自動的に環境変数 `PYTHONPATH` の最優先パスに結合されて起動し、対象プロセス内の `rouge_score` のデフォルトトークナイザーを Hugging Face の多言語モデル（`bert-base-multilingual-cased`）に自動的に上書き・差し替えます。
