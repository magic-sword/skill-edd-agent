try:
    from .creator import SkillCreationEngine
except (ImportError, ValueError):
    from creator import SkillCreationEngine

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
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Skill Creator Entrypoint CLI")
    parser.add_argument("prompt", type=str, nargs="?", default="", help="Natural language requirement prompt for the skill")
    parser.add_argument("--name", type=str, default=None, help="Skill identifier (e.g. pdf-tools)")
    parser.add_argument("--pattern", type=str, default=None, help="Skill pattern (workflow, task_based, reference, capabilities)")
    parser.add_argument("--output", type=str, default="src/skills", help="Output directory for generated skill")
    args = parser.parse_args()

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    res = create_skill(
        prompt=args.prompt,
        name=args.name,
        pattern=args.pattern,
        output_dir=args.output
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))

