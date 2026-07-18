from pydantic import BaseModel, Field
from typing import Literal, Union, Any

class EvalRunResult(BaseModel):
    passed: int = Field(..., description="合格したテストの件数")
    failed: int = Field(..., description="不合格だったテストの件数")
    total: int = Field(..., description="テストの総件数")
    accuracy: float = Field(..., description="テストの合格精度（0.0〜1.0）")
    detail_file_path: str | None = Field(None, description="ADKが生成した詳細結果JSONファイルの絶対パス")


class WorkspaceArtifacts(BaseModel):
    """Gymnasium ワークスペース環境からエクスポートされる成果物のスキーマ定義。"""
    modified_files: dict[str, str] = Field(
        default_factory=dict,
        description="新規作成または修正されたファイルの相対パスとコンテンツのマップ（キー: 相対パス, 値: ファイル内容）"
    )
    deleted_files: dict[str, str] | list[str] = Field(
        default_factory=list,
        description="削除されたファイルの相対パスのリスト"
    )


class WriteFileAction(BaseModel):
    """指定された相対パスのファイルにコンテンツを上書きで書き込むアクション定義。
    
    親ディレクトリが存在しない場合は、書き込み時に自動的に新規作成されます。
    """
    action: Literal["write_file"] = Field(
        "write_file", 
        description="アクション名（'write_file' 固定）"
    )
    path: str = Field(
        ..., 
        description="書き込み先となるファイルのプロジェクト相対パス（例: src/logic.py）。"
    )
    content: str = Field(
        ..., 
        description="ファイルに書き込むテキスト中身の文字列（Pythonコードや設定テキストなど）。"
    )


class ViewFileAction(BaseModel):
    """指定された相対パスのファイルの中身を読み込んで取得するアクション定義。"""
    action: Literal["view_file"] = Field(
        "view_file", 
        description="アクション名（'view_file' 固定）"
    )
    path: str = Field(
        ..., 
        description="読み取り対象となるファイルのプロジェクト相対パス。"
    )


class RunPytestAction(BaseModel):
    """一時サンドボックス環境内で pytest を実行し、検証結果を返すアクション定義。"""
    action: Literal["run_pytest"] = Field(
        "run_pytest", 
        description="アクション名（'run_pytest' 固定）"
    )


# 統合アクションモデル
WorkspaceAction = Union[WriteFileAction, ViewFileAction, RunPytestAction]


class FileState(BaseModel):
    """サンドボックス内の個別ファイルの状態を表すモデル。"""
    size: int = Field(..., description="ファイルのサイズ（バイト単位）")
    exists: bool = Field(..., description="ファイルがサンドボックス内に存在するかどうか")


class WorkspaceObservation(BaseModel):
    """Gymnasium環境から返却される観測値（Observation）のスキーマ定義。"""
    files: dict[str, FileState] = Field(
        default_factory=dict,
        description="サンドボックス内に存在するファイルの相対パスと状態のマップ（キー: 相対パス）"
    )
    pytest_output: str = Field(
        "",
        description="最後に実行された pytest の標準出力および標準エラーログ。未実行時は空文字。"
    )
    status: str = Field(
        "idle",
        description="直前のアクションの実行結果ステータス（例: 'file_written', 'pytest_passed', 'pytest_failed'）"
    )

from typing import Protocol, Tuple, Dict, Any, runtime_checkable

@runtime_checkable
class WorkspaceEnvProtocol(Protocol):
    """スキルやツールが動作するために要求する、ワークスペース環境のインターフェース。"""
    
    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[WorkspaceObservation, Dict[str, Any]]:
        """環境を初期状態にリセットします。"""
        ...
        
    def step(self, action: WorkspaceAction) -> Tuple[WorkspaceObservation, float, bool, bool, Dict[str, Any]]:
        """アクションを実行し、環境を1ステップ進めます。"""
        ...
        
    def close(self) -> None:
        """環境を終了し、後片付けを行います。"""
        ...
        
    def export_artifacts(self) -> WorkspaceArtifacts:
        """初期状態からの変更・新規作成・削除された差分ファイルを抽出します。"""
        ...


@runtime_checkable
class TestGenerator(Protocol):
    """仕様定義からテストケースJSONを生成し、指定パスに保存するプロトコル。"""
    def generate_tests(self, skill_name: str, output_path: str) -> bool:
        ...


@runtime_checkable
class TestExecutor(Protocol):
    """テストケースJSONをロードし、テストを実行・アサーションするプロトコル。"""
    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        ...



class EvalCase(BaseModel):
    eval_case_id: str = Field(..., description="テストケースを一意に識別するID")
    function_name: str = Field(..., description="テスト対象となるスキルの公開関数名")
    inputs: dict[str, Any] = Field(default_factory=dict, description="関数呼び出し時に渡す引数のマッピング")
    expected: str = Field("success", description="期待されるテスト結果（'success' または 期待する例外クラス名）")
    mock_responses: dict[str, Any] = Field(default_factory=dict, description="モック応答マッピング")


class EvalCaseSet(BaseModel):
    eval_set_id: str = Field(..., description="評価用テストセット全体の識別ID")
    eval_cases: list[EvalCase] = Field(..., description="テストケースのリスト")


# 軌跡シミュレーション評価用のデータモデル
class ToolUse(BaseModel):
    name: str = Field(..., description="呼び出すツール関数名")
    args: dict[str, Any] = Field(..., description="ツール関数に引き渡す引数")

class IntermediateData(BaseModel):
    tool_uses: list[ToolUse] = Field(..., description="中間ツール呼び出しのリスト")

class ConversationTurn(BaseModel):
    invocation_id: str = Field(..., description="ターンの識別子 (例: inv_pos_001)")
    user_content: dict[str, Any] = Field(..., description="ユーザーからの入力コンテンツ構造")
    final_response: dict[str, Any] = Field(..., description="モデルからの期待される最終返答コンテンツ構造")
    intermediate_data: IntermediateData = Field(..., description="中間ツール呼び出し情報")

class SessionInput(BaseModel):
    app_name: str = Field(..., description="評価を実行するアプリケーション名")
    user_id: str = Field(..., description="ユーザーID")

class TrajectoryEvalCase(BaseModel):
    eval_id: str = Field(..., description="評価ケースのユニーク識別子")
    conversation: list[ConversationTurn] = Field(..., description="会話のターンのリスト")
    session_input: SessionInput = Field(..., description="セッション初期ステート")

class TrajectoryEvalSet(BaseModel):
    eval_set_id: str = Field(..., description="評価セットID")
    name: str = Field(..., description="評価セットの名称")
    eval_cases: list[TrajectoryEvalCase] = Field(..., description="全評価テストケースのリスト")

