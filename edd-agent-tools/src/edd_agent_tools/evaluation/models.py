from pydantic import BaseModel, Field
from typing import Literal, Union

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
