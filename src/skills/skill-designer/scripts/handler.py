from .models import SkillDesignerOutput
from .executor import SkillExecutor

def skill_designer(prompt: str, summary: str | None = None, output_dir: str | None = None, skill: str | None = None, source_code_dir: str | None = None, target_entry: str | None = None) -> SkillDesignerOutput:
    """スキル設計要件に基づいて新しいスキルを設計し、または既存スキルを再設計するツール。

    Args:
        prompt: 設計するスキルの機能要件や追加の改修要望を記述した自然言語のテキスト。
        summary: スキルの仕様概要（ビジネス目的や要求の要約）。指定した場合、Geminiによる自動要約より優先して design.json の summary フィールドに保存されます。
        output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。省略時はskillから自動探索されます。
        skill: 既存のスキル名。再設計時の自動探索キーとして使用されます。
        source_code_dir: 再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。指定しない場合、自動的に検出を試みます。
        target_entry: 優先する論理配置先名。

    Returns:
        実行結果オブジェクト (SkillDesignerOutput)。
    """
    executor = SkillExecutor()
    return executor.skill_designer(prompt=prompt, summary=summary, output_dir=output_dir, skill=skill, source_code_dir=source_code_dir, target_entry=target_entry)
