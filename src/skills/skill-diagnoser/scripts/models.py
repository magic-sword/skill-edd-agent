from pydantic import BaseModel, Field
from typing import Literal, Any
from enum import StrEnum


class TargetLayer(StrEnum):
    """修正を適用すべきシステムの階層・レイヤー。"""
    SPEC = "spec"              # SKILL.md の修正（トリガー説明文、意思決定ツリー、手順）
    SCRIPT = "script"          # scripts/*.py の実装ロジック修正
    REFERENCE = "reference"    # references/*.md のドキュメント修正
    ASSET = "asset"            # assets/ のテンプレート修正
    TEST_CASE = "test_case"    # tests/*.evalset.json の不備・期待値修正


class FailureCategory(StrEnum):
    """テスト失敗の原因分類。"""
    TRIGGER_MISMATCH = "trigger_mismatch"            # トリガー説明とテストクエリの不一致
    SCHEMA_VALIDATION_ERROR = "schema_validation"    # 入出力型・必須チェック違反
    LOGIC_EXCEPTION = "logic_exception"              # ゼロ除算、KeyError、IndexError等の実行時例外
    MOCK_UNHANDLED = "mock_unhandled"                # GeminiClient等の外部モック未設定
    MISSING_IMPLEMENTATION = "missing_implementation"# 関数や変数の未定義
    TEST_EXPECTATION_BUG = "test_expectation_bug"    # テスト期待値側の誤り


class SpecPatch(BaseModel):
    """SKILL.md に対する修正データモデル。"""
    model_config = {"extra": "ignore"}
    description_patch: str | None = Field(
        None, description="更新後のスキル説明文（トリガー精度向上用）"
    )
    decision_tree_patch: list[dict[str, str]] | None = Field(
        None, description="更新後の意思決定ツリー項目（condition, action）"
    )
    instructions_patch: list[str] | None = Field(
        None, description="更新後の手順指示"
    )


class ScriptPatchInstruction(BaseModel):
    """scripts/*.py に対するコード修正指示モデル。"""
    model_config = {"extra": "ignore"}
    target_file: str = Field(
        "scripts/main.py", description="修正対象ファイルの相対パス（例: scripts/analyze.py）"
    )
    problematic_code_snippet: str | None = Field(
        None, description="問題のある既存コード箇所"
    )
    fix_instructions: str = Field(
        "", description="どのようにコードを修正すべきかの具体的指示"
    )
    suggested_code: str | None = Field(
        None, description="推奨される修正後コードスニペット"
    )


class TestCasePatch(BaseModel):
    """テストケース定義（evalset.json）に対する修正指示モデル。"""
    model_config = {"extra": "ignore"}
    evalset_path: str | None = Field(None, description="修正対象の evalset.json パス")
    case_id: str | None = Field(None, description="修正対象のテストケースID")
    suggested_fix: str | None = Field(None, description="テストケースの修正指示")


class ImprovementPlan(BaseModel):
    """診断結果および構造化された改善計画モデル。"""
    model_config = {"extra": "ignore"}
    skill_name: str = Field(..., description="診断対象スキルの論理名")
    test_type: str = Field(..., description="失敗したテスト種別（例: contract, trigger）")
    verdict: Literal["needs_improvement", "no_issues_found", "unrecoverable"] = Field(
        "needs_improvement", description="診断判定結果 ('needs_improvement', 'no_issues_found', 'unrecoverable')"
    )
    target_layer: TargetLayer = Field(..., description="修正対象レイヤー")
    failure_category: FailureCategory = Field(..., description="失敗の原因カテゴリ")
    root_cause: str = Field(..., description="根本原因の分析詳細サマリー")
    recommended_action: str = Field(..., description="後続フェーズで実行すべき推奨アクション")
    spec_patch: SpecPatch | None = Field(
        None, description="仕様層（SKILL.md）修正時の差分データ"
    )
    script_patch: ScriptPatchInstruction | None = Field(
        None, description="ロジック層（scripts/*.py）修正時の指示データ"
    )
    test_case_patch: TestCasePatch | None = Field(
        None, description="テストケース層修正時の指示データ"
    )


class DiagnoseSkillFailureOutput(BaseModel):
    """diagnose_skill_failure 関数の返却出力モデル。"""
    status: Literal["success", "failed"] = Field(..., description="診断処理の実行ステータス")
    details: str = Field(..., description="診断結果サマリーまたはエラーメッセージ")
    plan: ImprovementPlan | None = Field(None, description="策定された改善計画オブジェクト")
