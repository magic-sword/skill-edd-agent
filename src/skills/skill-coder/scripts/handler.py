from .models import SkillCoderOutput
from .executor import SkillExecutor

def skill_coder(prompt: str | None = None, skill: str | None = None, design_path: str | None = None, output_dir: str | None = None) -> SkillCoderOutput:
    """設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コードを自動生成・更新するワークフロー。

    Args:
        prompt: 実装したいビジネスロジックの機能要件や詳細な指示。
        skill: 対象のスキル名。design_pathが省略された場合の探索キー。
        design_path: 対象スキルの design.json への絶対/相対パス。
        output_dir: コードの出力先ディレクトリ。省略時は対象スキルのルートディレクトリ。

    Returns:
        実行結果オブジェクト (SkillCoderOutput)。
    """
    executor = SkillExecutor()
    return executor.skill_coder(prompt=prompt, skill=skill, design_path=design_path, output_dir=output_dir)
