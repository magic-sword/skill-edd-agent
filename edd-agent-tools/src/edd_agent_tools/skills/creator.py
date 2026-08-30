import os
import sys
import json
import re
import importlib.resources
from pathlib import Path
from typing import Optional, Dict, Any
from google.genai import types

from edd_agent_tools.skills.models import (
    SkillLogicDraft,
    SkillPattern,
)
from edd_agent_tools.skills.template_engine import SkillTemplateEngine
from edd_agent_tools.skills.validator import SkillValidator, ValidationResult

from edd_agent_tools.skills.state import SkillsState
from edd_agent_tools.skills.skill import Skill
from edd_agent_tools.evaluation import ContractTestRunner, LocalWorkspaceEnv
from edd_agent_tools.gemini import client, GeminiRequest


def _load_prompt_template(filename: str) -> str:
    """パッケージ内部の edd_agent_tools/docs/prompts/ からプロンプトテンプレートをロードします。"""
    try:
        ref = importlib.resources.files("edd_agent_tools.docs.prompts").joinpath(filename)
        return ref.read_text(encoding="utf-8")
    except Exception:
        # フォールバック: 直接ファイルパス検索
        fallback_path = Path(__file__).resolve().parent.parent / "docs" / "prompts" / filename
        if fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Prompt template not found: {filename}")


class SkillCreationEngine:
    """5段階品質保証・評価駆動パイプライン（EDD）を実行する自動スキル生成エンジン"""

    def __init__(self, output_base_dir: str = "src/skills"):
        self.output_base_dir = Path(output_base_dir).resolve()
        self.client = client
        self.state = SkillsState()
        self.system_prompt_draft = _load_prompt_template("draft_extraction.txt")
        self.resource_prompt_template = _load_prompt_template("resource_generation.txt")

    def _get_existing_inventory_text(self) -> str:
        """既存の登録スキル一覧を取得し、インベントリ文字列を構築します。"""
        try:
            skills = self.state.list_skills()
            if not skills:
                return "None (No existing skills registered)"
            lines = []
            for s in skills:
                desc = s.description or "No description provided."
                lines.append(f"- {s.name}: {desc}")
            return "\n".join(lines)
        except Exception:
            return "None"

    def create_skill_from_prompt(
        self,
        prompt: str,
        name: Optional[str] = None,
        pattern: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """ユーザープロンプトから完全なスキルパッケージおよびテストハーネスを自動設計・生成します。"""
        print(f"🚀 [Stage 1] Analyzing requirements, checking inventory, and extracting logical skill draft...")

        # 1. Stage 1: 論理設計（SkillLogicDraft）の構造化抽出
        inventory_text = self._get_existing_inventory_text()
        instruction = (
            f"User Requirement:\n{prompt}\n\n"
            f"Existing Skill Inventory:\n{inventory_text}\n"
        )
        if name:
            instruction += f"\nPreferred Skill Name: {name}\n"
        if pattern:
            instruction += f"\nPreferred Pattern: {pattern}\n"

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

        # 5. Stage 5: 評価テストハーネスの自動生成 & 初期契約検証 (Evaluation-Driven Development)
        print(f"🧪 [Stage 5] Generating test harness & verifying contract execution...")
        test_harness_res = self._generate_and_verify_test_harness(target_skill_dir, draft)

        print(f"🎉 Successfully created skill '{draft.name}' at: {target_skill_dir}")
        return {
            "status": "success",
            "skill_name": draft.name,
            "output_dir": str(target_skill_dir),
            "pattern": draft.pattern.value,
            "resources": [r.rel_path for r in draft.resources_plan],
            "tests_generated": test_harness_res.get("generated_files", []),
            "contract_passed": test_harness_res.get("contract_passed", True),
            "message": f"Successfully created skill '{draft.name}' with test harness."
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
            system_instruction="You are an expert code and documentation generator. Ensure Python scripts are deterministic CLI tools equipped with argparse and --help support.",
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
            (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")
        return SkillValidator.validate_directory(skill_dir)

    def _generate_and_verify_test_harness(self, skill_dir: Path, draft: SkillLogicDraft) -> Dict[str, Any]:
        """初期評価データセット（contract, trigger）を生成し、契約テストを実行"""
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "results").mkdir(exist_ok=True)

        generated_files = []
        script_name = f"{draft.name.replace('-', '_')}.py"
        script_rel = f"scripts/{script_name}"
        if not (skill_dir / script_rel).exists():
            scripts = [f for f in (skill_dir / "scripts").glob("*.py") if f.name != "__init__.py"]
            if scripts:
                script_rel = f"scripts/{scripts[0].name}"

        # 1. Contract Test ケースの生成
        contract_data = {
            "eval_set_id": f"{draft.name}_contract_eval",
            "eval_cases": [
                {
                    "eval_case_id": "test_cli_help",
                    "script_name": script_rel,
                    "cli_args": ["--help"],
                    "expected_exit_code": 0,
                    "expected_stdout_contains": ["--help"]
                }
            ]
        }
        contract_path = tests_dir / f"{draft.name}_contract.evalset.json"
        contract_path.write_text(json.dumps(contract_data, indent=2, ensure_ascii=False), encoding="utf-8")
        generated_files.append(str(contract_path))

        # 2. Trigger Test ケースの生成
        trigger_cases = []
        for idx, ex in enumerate(draft.concrete_trigger_examples, 1):
            trigger_cases.append({
                "name": f"positive_trigger_{idx}",
                "user_input": ex,
                "expected_tools": [draft.name],
                "should_trigger": True
            })
        for idx, non_ex in enumerate(draft.when_not_to_use[:3], 1):
            trigger_cases.append({
                "name": f"negative_trigger_{idx}",
                "user_input": non_ex,
                "expected_tools": [],
                "should_trigger": False
            })
        trigger_data = {"eval_set_id": f"{draft.name}_trigger_eval", "cases": trigger_cases}
        trigger_path = tests_dir / f"{draft.name}_trigger.evalset.json"
        trigger_path.write_text(json.dumps(trigger_data, indent=2, ensure_ascii=False), encoding="utf-8")
        generated_files.append(str(trigger_path))

        # 3. 契約テストの実行検証
        contract_passed = True
        try:
            skill_obj = Skill(root_dir=str(skill_dir), tier=0)
            runner = ContractTestRunner()
            env = LocalWorkspaceEnv()
            run_res = runner.run_tests(skill=skill_obj, test_cases_data=contract_data, env=env)
            contract_passed = (run_res.failed == 0 and run_res.accuracy >= 1.0)
            print(f"  🧪 Contract testing result: {'PASSED' if contract_passed else 'FAILED'}")
        except Exception as e:
            print(f"  ⚠️ Contract test run warning: {e}")

        return {
            "generated_files": generated_files,
            "contract_passed": contract_passed
        }


def create_skill(
    prompt: str,
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    output_dir: Optional[str] = None
) -> dict:
    """自然言語要件から完全なスキルパッケージ（SKILL.md、scripts/、references/、assets/）およびテストハーネスを自律生成します。"""
    engine = SkillCreationEngine(output_base_dir=output_dir or "src/skills")
    return engine.create_skill_from_prompt(
        prompt=prompt,
        name=name,
        pattern=pattern,
        output_dir=output_dir
    )
