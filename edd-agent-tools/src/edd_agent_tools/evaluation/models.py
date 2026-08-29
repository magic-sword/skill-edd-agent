from pydantic import BaseModel, Field
from typing import Literal, Union, Any

class EvalRunResult(BaseModel):
    passed: int = Field(..., description="合格したテストの件数")
    failed: int = Field(..., description="不合格だったテストの件数")
    total: int = Field(..., description="テストの総件数")
    accuracy: float = Field(..., description="テストの合格精度（0.0〜1.0）")
    detail_file_path: str | None = Field(None, description="詳細結果JSONファイルの絶対パス")


class FailedCaseDetail(BaseModel):
    """不合格となったテストケースの詳細情報。"""
    eval_case_id: str = Field(..., description="テストケースの一意な識別ID")
    function_name: str = Field(..., description="テスト対象となった公開関数名")
    inputs: dict[str, Any] = Field(default_factory=dict, description="テストケース実行時に渡された入力引数")
    expected: str = Field(..., description="期待されていた結果または例外")
    actual: Any = Field(None, description="実際の返却値または発生した例外の文字列表現")
    error_type: str | None = Field(None, description="発生したエラー・例外の型名（例: ValidationError, TypeError, ValueError）")
    error_message: str | None = Field(None, description="エラーの詳細メッセージ")
    traceback: str | None = Field(None, description="例外発生時のスタックトレース")


class EvalDetailReport(BaseModel):
    """テスト実行全体の詳細レポートモデル。"""
    skill_name: str = Field(..., description="テスト対象スキルの論理名")
    test_type: str = Field(..., description="実行されたテスト種別（例: contract, trigger, golden, judge, adversarial）")
    timestamp: str = Field(..., description="テスト実行日時のISO 8601文字列")
    passed: int = Field(..., description="合格したテストケース件数")
    failed: int = Field(..., description="不合格だったテストケース件数")
    total: int = Field(..., description="実行された全テストケース件数")
    accuracy: float = Field(..., description="合格精度（0.0〜1.0）")
    details: str = Field("", description="テスト結果のサマリー説明")
    failed_cases: list[FailedCaseDetail] = Field(default_factory=list, description="不合格となったテストケース一覧")
    metrics: dict[str, Any] = Field(default_factory=dict, description="その他の評価メトリクス（スコア、Rouge-1等）")



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
    """スキルやツールが安全に動作・試行錯誤するための、隔離されたワークスペース環境のインターフェース。
    
    Gymnasium 互換のステップ実行およびリセット機構を提供し、環境変更の追跡とロールバックをカプセル化します。
    """
    
    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[WorkspaceObservation, Dict[str, Any]]:
        """環境を初期状態（クローン直後、または変更の破棄後）にリセットします。
        
        Args:
            seed: 乱数シード（任意）。
            options: リセット時の挙動を制御するオプション辞書（任意）。
            
        Returns:
            Tuple[WorkspaceObservation, Dict[str, Any]]: 
                - WorkspaceObservation: 初期化後のファイル状態やテスト出力を含む観測オブジェクト。
                - Dict[str, Any]: 環境固有のメタデータを含む追加情報辞書。
        """
        ...
        
    def step(self, action: WorkspaceAction) -> Tuple[WorkspaceObservation, float, bool, bool, Dict[str, Any]]:
        """環境に対して指定されたアクションを実行し、環境のステートを1ステップ進めます。
        
        Args:
            action: 実行する環境操作アクション（WriteFileAction, ViewFileAction, RunPytestAction 等）。
            
        Returns:
            Tuple[WorkspaceObservation, float, bool, bool, Dict[str, Any]]:
                - WorkspaceObservation: アクション適用後の新しい環境観測オブジェクト。
                - float: アクションの評価結果に対する即時報酬（シミュレーション評価用）。
                - bool: 終了判定（terminated）。目標達成または失敗で環境が完全に終了したか。
                - bool: 打ち切り判定（truncated）。最大ステップ数到達などで処理が途切れたか。
                - Dict[str, Any]: デバッグログや追加のメタデータを含む情報辞書。
        """
        ...
        
    def close(self) -> None:
        """環境をクローズし、一時ディレクトリの削除やリソースの解放などの後片付けを行います。"""
        ...
        
    def export_artifacts(self) -> WorkspaceArtifacts:
        """環境の初期状態（reset直後）から、現在までのファイル差分（作成・変更・削除）を抽出します。
        
        Returns:
            WorkspaceArtifacts: 本番へ適用可能なファイルの追加・修正・削除差分オブジェクト。
        """
        ...


@runtime_checkable
class TestGenerator(Protocol):
    """スキルの仕様定義からテストケースアセットを自動生成し、ファイルに書き出すプロトコル。"""
    
    def generate_tests(self, skill_name: str, output_path: str) -> bool:
        """指定されたスキルの仕様（SKILL.md）からテストケースを自動生成して保存します。
        
        Args:
            skill_name: テストケースの生成対象となるスキルの論理名。
            output_path: 生成されたテストケースJSONを書き出す物理ファイルパス。
            
        Returns:
            bool: テストケースの生成および保存に成功した場合は True、失敗した場合は False。
        """
        ...


@runtime_checkable
class TestExecutor(Protocol):
    """テストケースをロードし、指定された隔離環境上で検証・アサーションを実行するプロトコル。"""
    
    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたテストケースファイルを読み込み、環境上でテストを実行して精度を検証します。
        
        Args:
            skill_name: テスト実行・アサーション対象となるスキルの論理名。
            eval_set_path: テストケースが格納された *.evalset.json ファイルの物理パス。
            env: テストが実行される WorkspaceEnvProtocol に準拠した仮想サンドボックス環境。
            
        Returns:
            EvalRunResult: 合格数、不合格数、実行総数、合格精度（0.0〜1.0）および詳細結果のパスを含む型安全な結果オブジェクト。
        """
        ...



from enum import StrEnum

class ExpectedResultType(StrEnum):
    SUCCESS = "success"
    VALUE_ERROR = "ValueError"
    TYPE_ERROR = "TypeError"
    RUNTIME_ERROR = "RuntimeError"
    KEY_ERROR = "KeyError"
    INDEX_ERROR = "IndexError"
    ZERO_DIVISION_ERROR = "ZeroDivisionError"
    EXCEPTION = "Exception"


class EvalCase(BaseModel):
    eval_case_id: str = Field(..., description="テストケースを一意に識別するID")
    function_name: str = Field(..., description="テスト対象となるスキルの公開関数名")
    inputs: dict[str, Any] = Field(default_factory=dict, description="関数呼び出し時に渡す引数のマッピング")
    expected: ExpectedResultType = Field(ExpectedResultType.SUCCESS, description="期待されるテスト結果 ('success' または定義された Python 例外クラス名のみ選択可能)")
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

