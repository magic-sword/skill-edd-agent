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
