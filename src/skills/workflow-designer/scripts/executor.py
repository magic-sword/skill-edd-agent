import os
import json
from .models import WorkflowDesignerOutput
from pydantic import TypeAdapter
from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools import WorkflowDesign, ModuleDesign
from .client import GeminiDesignClient
from .prompter import DesignPrompter
from .resolver import PathResolver
from .cleanser import DesignCleanser
from .skeleton_models import SkeletonDesign
from google.genai import types

class SkillExecutor:
    """
    ワークフロー設計要件から ADK 2.0 互換の ワークフロー用 design.json を設計して出力する
    オブジェクト指向エグゼキューター。
    """
    def __init__(self):
        self._path_resolver = PathResolver()
        self._gemini_client = GeminiDesignClient()
        self._state = SkillsState()

    def workflow_designer(self, prompt: str, summary: str = None, output_dir: str = None, target_entry: str = "workflow") -> WorkflowDesignerOutput:
        """
        ワークフロー設計のメインロジックを実行します。
        """
        # 1. パス解決（新規ワークフロー用に名前を自動解決させるため、 skill_name は None とする）
        # target_entry を "workflow" とすることで、src/workflows に解決される
        resolved_paths = self._path_resolver.resolve_paths(skill_name=None, output_dir=output_dir, target_entry=target_entry)
        
        output_dir = resolved_paths["output_dir"]
        skill_directory = resolved_paths["skill_directory"]

        # 2. DesignPrompter の初期化
        designer_skill = self._state.get_skill("workflow-designer")
        design_prompter = DesignPrompter(designer_skill=designer_skill)

        # 3. L1 用メタデータ（既存全スキルのリストと説明）を構築
        discovered_skills = self._state.scan_skills(force_reload=True)
        l1_elements = []
        for s_name, s_obj in discovered_skills.items():
            try:
                fm = s_obj.load_design()
                l1_elements.append(f"""- スキル名: {fm.name}
  トリガー条件と作用: {fm.description}""")
            except Exception:
                pass
        l1_skills_context = "\n".join(l1_elements) if l1_elements else "なし"

        # L1 (骨組み) リクエスト作成
        l1_request = design_prompter.build_l1_request(
            client=self._gemini_client._client,
            prompt=prompt,
            l1_skills_context=l1_skills_context
        )

        try:
            skeleton_design = self._generate_l1_design(l1_request)
        except Exception as e:
            return WorkflowDesignerOutput(status="failed", message=f"第一段階（L1粗設計）生成またはパースエラー: {e}", output_dir="")

        # 4. L2 用メタデータ（骨組みで選択されたステップの型シグネチャ）をオンデマンド構築
        l2_skills_context = self._get_l2_skills_context(skeleton_design.get("steps", []))

        # L2 (引数マッピング・精緻化) リクエスト作成
        l2_request = design_prompter.build_l2_request(
            client=self._gemini_client._client,
            skeleton_design_str=json.dumps(skeleton_design, indent=2, ensure_ascii=False),
            l2_skills_context=l2_skills_context
        )

        # L2 呼び出し: 最終設計の生成
        try:
            design_data = self._generate_l2_design(l2_request, summary_override=summary)
        except Exception as e:
            return WorkflowDesignerOutput(status="failed", message=f"第二段階（L2引数マッピング）生成またはパースエラー: {e}", output_dir="")

        # 5. スキーマバリデーション (WorkflowDesign)
        try:
            TypeAdapter(ModuleDesign).validate_python(design_data)
        except Exception as e:
            return WorkflowDesignerOutput(
                status="failed", 
                message=f"設計データのバリデーションエラー（ワークフロー構成不整合など）: {e}", 
                output_dir=""
            )

        # 6. design.json の保存
        try:
            self._save_design(design_data, skill_directory.design_path)
        except Exception as e:
            return WorkflowDesignerOutput(status="failed", message=f"design.json の保存エラー: {e}", output_dir="")

        message = f"ワークフロー設計書 design.json が '{skill_directory.design_path}' に正常に生成されました。"
        return WorkflowDesignerOutput(status="success", message=message, output_dir=output_dir)

    def _generate_l1_design(self, l1_request: types.GenerateContentRequest) -> dict:
        """L1設計を生成します。"""
        skeleton_text = self._gemini_client.generate_design(contents=l1_request, response_schema=SkeletonDesign)
        if "```" in skeleton_text:
            skeleton_text = "\n".join([line for line in skeleton_text.split("\n") if not line.strip().startswith("```")])
        return json.loads(skeleton_text)

    def _get_l2_skills_context(self, steps: list) -> str:
        """L2設計用の依存スキルのコンテキストを生成します。"""
        l2_elements = []
        if steps and isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("type") == "skill":
                    target_skill = step.get("target")
                    if target_skill:
                        try:
                            dep_skill = self._state.get_skill(target_skill)
                            dep_design = dep_skill.load_design()
                            
                            inputs_def = []
                            outputs_def = []
                            
                            if getattr(dep_design, "functions", None):
                                for fn in dep_design.functions:
                                    inputs_def.append(f"  - 関数 {fn.name} の入力:")
                                    for p in fn.parameters:
                                        inputs_def.append(f"    * {p.name} ({p.type}) {'(必須)' if p.required else '(任意)'}: {p.description}")
                                    
                                    if fn.response_parameters:
                                        outputs_def.append(f"  - 関数 {fn.name} の出力:")
                                        for p in fn.response_parameters:
                                            outputs_def.append(f"    * {p.name} ({p.type}): {p.description}")
                            elif dep_design.parameters:
                                inputs_def.append(f"  - 入力パラメータ:")
                                for p in dep_design.parameters:
                                    inputs_def.append(f"    * {p.name} ({p.type}) {'(必須)' if p.required else '(任意)'}: {p.description}")
                                if dep_design.response_parameters:
                                    outputs_def.append(f"  - 出力戻り値:")
                                    for p in dep_design.response_parameters:
                                        outputs_def.append(f"    * {p.name} ({p.type}): {p.description}")
                            
                            inputs_def_str = "\n".join(inputs_def) if inputs_def else "    なし"
                            outputs_def_str = "\n".join(outputs_def) if outputs_def else "    なし"

                            l2_elements.append(
                                f"■ スキル名: {dep_design.name}\n"
                                f"  説明: {dep_design.description}\n"
                                f"  入力パラメータ仕様:\n{inputs_def_str}\n"
                                f"  出力戻り値仕様:\n{outputs_def_str}\n"
                            )
                        except Exception as e:
                            print(f"Warning: Failed to load design for {target_skill}: {e}")
        return "\n".join(l2_elements) if l2_elements else "なし"

    def _generate_l2_design(self, l2_request: types.GenerateContentRequest, summary_override: str | None) -> dict:
        """L2設計を生成します。"""
        response_text = self._gemini_client.generate_design(contents=l2_request, response_schema=ModuleDesign)
        if "```" in response_text:
            response_text = "\n".join([line for line in response_text.split("\n") if not line.strip().startswith("```")])
        
        design_data = json.loads(response_text)
        
        # クレンジング
        design_data = DesignCleanser().clean(design_data)

        if summary_override:
            design_data["summary"] = summary_override
            
        return design_data

    def _save_design(self, design_data: dict, design_file_path: str):
        """設計データをファイルに保存します。"""
        assets_dir = os.path.dirname(design_file_path)
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        with open(design_file_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, indent=2, ensure_ascii=False)
