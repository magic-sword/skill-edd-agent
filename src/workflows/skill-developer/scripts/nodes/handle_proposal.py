import os
import sys
from google.adk.tools import ToolContext


def _load_warning_template() -> str:
    """警告メッセージテンプレートファイルを読み込みます。"""
    current_dir = os.path.dirname(__file__)
    template_path = os.path.join(current_dir, "../../assets/templates/proposal_warning_template.txt")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"警告テンプレートファイルが見つかりません: {template_path}")


def run_handle_proposal_step(tool_context: ToolContext) -> str:
    """
    要件難易度が高すぎ既存スキルが不足している判定（proposal）時に実行されるノード。
    developer-router から伝播された分析理由 (rationale) と 提案スキル (proposed_skill) を取得し、
    アセット化されたテンプレートに埋め込んで警告を出力し、ワークフローを安全に完了（中断）させます。
    """
    rationale = tool_context.state.get("rationale", "要件の難易度が高く、前提となるスキルが不足しています。")
    proposed_skill = tool_context.state.get("proposed_skill")

    # 提案スキルの詳細テキスト作成
    if proposed_skill and isinstance(proposed_skill, dict):
        skill_name = proposed_skill.get("name", "未定義スキル")
        skill_desc = proposed_skill.get("description", "説明なし")
        proposal_str = f"  - スキル名: {skill_name}\n  - 概要: {skill_desc}"
    elif hasattr(proposed_skill, "name"):
        skill_name = getattr(proposed_skill, "name", "未定義スキル")
        skill_desc = getattr(proposed_skill, "description", "説明なし")
        proposal_str = f"  - スキル名: {skill_name}\n  - 概要: {skill_desc}"
        proposed_skill = {"name": skill_name, "description": skill_desc}
    else:
        proposal_str = "  - （具体的なスキル提案なし）"

    # テンプレートのロードとフォーマット
    template = _load_warning_template()
    warning_message = template.format(
        rationale=rationale,
        proposal_str=proposal_str
    )

    print(warning_message, file=sys.stderr)

    # ワークフローの状態に警告結果を設定
    tool_context.state["status"] = "halted"
    tool_context.state["message"] = warning_message
    tool_context.state["proposed_skill"] = proposed_skill
    if tool_context.state.get("output_dir") is None:
        tool_context.state["output_dir"] = ""

    return warning_message
