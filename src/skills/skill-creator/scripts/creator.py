import os
import sys
import json
import re
from pathlib import Path
from typing import Optional
from google.genai import types

from edd_agent_tools.skills import (
    SkillLogicDraft,
    SkillPattern,
    SkillTemplateEngine,
    SkillValidator,
    ValidationResult
)
from edd_agent_tools.gemini import client, GeminiRequest

# プロンプトテンプレートのディレクトリパス
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "prompts"

def _load_prompt_template(filename: str) -> str:
    """assets/prompts/ 配下のプロンプトテンプレートファイルをロードします。"""
    template_path = PROMPTS_DIR / filename
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")

class SkillCreationEngine:
    """4段階品質保証パイプラインを実行する自動スキル生成エンジン"""

    def __init__(self, output_base_dir: str = "src/skills"):
        self.output_base_dir = Path(output_base_dir).resolve()
        self.client = client
        self.system_prompt_draft = _load_prompt_template("draft_extraction.txt")
        self.resource_prompt_template = _load_prompt_template("resource_generation.txt")

    def create_skill_from_prompt(
        self,
        prompt: str,
        name: Optional[str] = None,
        pattern: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """ユーザープロンプトから完全なスキルパッケージを自動設計・生成します。"""
        print(f"🚀 [Stage 1] Analyzing requirements and extracting logical skill draft...")

        # 1. Stage 1: 論理設計（SkillLogicDraft）の構造化抽出
        instruction = f"User Requirement:\n{prompt}\n"
        if name:
            instruction += f"Preferred Skill Name: {name}\n"
        if pattern:
            instruction += f"Preferred Pattern: {pattern}\n"

        req = GeminiRequest(
            prompt=instruction,
            client=self.client
        )

        response = req.execute(
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt_draft,
                response_mime_type="application/json",
                response_schema=SkillLogicDraft,
                temperature=0.2
            )
        )

        draft_dict = json.loads(response.text)
        draft = SkillLogicDraft.model_validate(draft_dict)

        # 出力先ディレクトリの決定
        if output_dir:
            target_skill_dir = Path(output_dir).resolve()
            if target_skill_dir.name != draft.name:
                target_skill_dir = target_skill_dir / draft.name
        else:
            target_skill_dir = self.output_base_dir / draft.name

        target_skill_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Target skill directory: {target_skill_dir}")

        # 2. Stage 2: 決定論的 Markdown レンダリング
        print(f"📝 [Stage 2] Rendering SKILL.md deterministically...")
        skill_md_content = SkillTemplateEngine.render(draft)
        (target_skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        # 3. Stage 3: リソースファイル群の生成と配置
        print(f"🛠️ [Stage 3] Generating bundled resources (scripts, references, assets)...")

        for res_plan in draft.resources_plan:
            self._generate_single_resource(target_skill_dir, res_plan, draft)

        # 4. Stage 4: 静的検証と自己修復ループ
        print(f"🔍 [Stage 4] Performing static validation & self-correction...")
        val_res = self._validate_and_self_correct(target_skill_dir, draft, max_retries=3)

        if not val_res.is_valid:
            print(f"⚠️ Skill creation completed with warnings/errors: {val_res.errors}")
            return {
                "status": "partial_success" if not val_res.errors else "failed",
                "skill_name": draft.name,
                "output_dir": str(target_skill_dir),
                "errors": val_res.errors,
                "warnings": val_res.warnings
            }

        print(f"🎉 Successfully created skill '{draft.name}' at: {target_skill_dir}")
        return {
            "status": "success",
            "skill_name": draft.name,
            "output_dir": str(target_skill_dir),
            "pattern": draft.pattern.value,
            "resources": [r.rel_path for r in draft.resources_plan],
            "message": f"Successfully created skill '{draft.name}'"
        }

    def _generate_single_resource(self, skill_dir: Path, res_plan, draft: SkillLogicDraft):
        """個別のスクリプト・ドキュメント・テンプレートを生成"""
        rel_path = res_plan.rel_path
        target_file = skill_dir / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)

        prompt = self.resource_prompt_template.format(
            rel_path=rel_path,
            name=draft.name,
            pattern=draft.pattern.value,
            overview=draft.overview_summary,
            purpose=res_plan.purpose
        )

        req = GeminiRequest(
            prompt=prompt,
            client=self.client
        )
        resp = req.execute(config=types.GenerateContentConfig(
            system_instruction="You are an expert code and documentation generator.",
            temperature=0.2
        ))
        raw_text = resp.text.strip()

        # バッククォートの除去（存在する場合）
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if len(lines) >= 2 and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        target_file.write_text(raw_text, encoding="utf-8")
        if rel_path.endswith(".py") or rel_path.endswith(".sh"):
            try:
                target_file.chmod(0o755)
            except Exception:
                pass
        print(f"  ✅ Created resource: {rel_path}")

    def _validate_and_self_correct(self, skill_dir: Path, draft: SkillLogicDraft, max_retries: int = 3) -> ValidationResult:
        """静的リンターを実行し、必要に応じて自己修復を行う"""
        for attempt in range(1, max_retries + 1):
            res = SkillValidator.validate_directory(skill_dir)
            if res.is_valid and not res.errors:
                return res

            print(f"  ⚠️ Validation issues detected (Attempt {attempt}/{max_retries}): {res.errors}")
            # エラーの自動修復
            skill_md_content = SkillTemplateEngine.render(draft)
        return SkillValidator.validate_directory(skill_dir)


def create_skill(
    prompt: str,
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    output_dir: Optional[str] = None
) -> dict:
    """自然言語要件から完全なスキルパッケージ（SKILL.md、scripts/、references/、assets/）を自律生成します。"""
    engine = SkillCreationEngine(output_base_dir=output_dir or "src/skills")
    return engine.create_skill_from_prompt(
        prompt=prompt,
        name=name,
        pattern=pattern,
        output_dir=output_dir
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Creation Engine CLI")
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


if __name__ == "__main__":
    main()

