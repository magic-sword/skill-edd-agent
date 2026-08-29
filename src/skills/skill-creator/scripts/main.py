import os
from typing import Optional
from .creator import SkillCreationEngine

__all__ = ["create_skill"]

def create_skill(
    prompt: str,
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    output_dir: Optional[str] = None
) -> dict:
    """自然言語要件から Markdown-First & Progressive Disclosure 準拠のスキルパッケージを自動生成・再設計します。

    Args:
        prompt: 作成・更新したいスキルの機能要件や仕様の自然言語テキスト。
        name: 希望するスキル識別子（ハイフンケース。省略時はLLMが自動推論）。
        pattern: スキル構造パターン（'workflow', 'task_based', 'reference', 'capabilities'。省略時は自動判定）。
        output_dir: スキルの出力先ディレクトリ（省略時は 'src/skills' 配下）。

    Returns:
        生成結果情報辞書（status, skill_name, output_dir, pattern, resources 等）。
    """
    engine = SkillCreationEngine(output_base_dir=output_dir or "src/skills")
    return engine.create_skill_from_prompt(
        prompt=prompt,
        name=name,
        pattern=pattern,
        output_dir=output_dir
    )

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python main.py <prompt> [--name <name>] [--pattern <pattern>]")
        sys.exit(1)
    prompt_arg = sys.argv[1]
    res = create_skill(prompt_arg)
    print(res)
