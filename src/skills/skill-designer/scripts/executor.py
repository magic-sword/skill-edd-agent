import os
import json
from google.adk.tools import ToolContext
from pydantic import TypeAdapter
from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools.models import ModuleDesign
from .models import Input, Output
from .client import GeminiDesignClient
from .prompter import DesignPrompter
from .resolver import PathResolver
from .parser import ConstraintParser
from .cleanser import DesignCleanser
from .skeleton_models import SkeletonDesign

class SkillExecutor:
    """
    自然言語の要件や既存のソースコードから ADK 2.0 互換の design.json を設計して出力する
    オブジェクト指向エグゼキューター。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context

    def execute(self) -> Output:
        prompt = self.params.prompt
        summary_override = self.params.summary
        output_dir = self.params.output_dir
        skill = self.params.skill
        source_code_dir = self.params.source_code_dir

        # 1. パス解決
        path_resolver = PathResolver()
        resolved_paths = path_resolver.resolve_paths(skill_name=skill, output_dir=output_dir, source_code_dir=source_code_dir)
        
        existing_name = resolved_paths["existing_name"]
        # ここで output_dir を更新する。元のparams.output_dirではなく解決されたパスを使用
        output_dir = resolved_paths["output_dir"]
        scan_target = resolved_paths["scan_target"]
        skill_directory = resolved_paths["skill_directory"]

        # 2. 既存の制約事項を抽出
        constraint_parser = ConstraintParser()
        existing_constraints_str = constraint_parser.get_existing_constraints(existing_name)

        # 3. Gemini API クライアントの初期化
        gemini_client = GeminiDesignClient()

        # 4. プロンプトコンテンツの構築
        from edd_agent_tools.skills import SkillsState
        state = SkillsState()
        
        # 4.1. L1メタデータの収集（全登録スキルの名前とトリガー説明）
        discovered_skills = state.scan_skills()
        l1_elements = []
        for s_name, s_obj in discovered_skills.items():
            try:
                fm = s_obj.load_design()
                l1_elements.append(f"- スキル名: {fm.name}\n  トリガー条件と作用: {fm.description}")
            except Exception:
                # パースエラーのある古いスキルはスキップ
                pass
        l1_skills_context = "\n".join(l1_elements) if l1_elements else "なし"

        designer_skill = state.get_skill("skill-designer")
        design_prompter = DesignPrompter(designer_skill=designer_skill)
        
        output_file_path = skill_directory.design_path
        existing_design_file_path = output_file_path if os.path.exists(output_file_path) else None

        # L1 (粗設計/骨組み) 用リクエストの作成
        l1_request = design_prompter.build_l1_request(
            client=gemini_client._client,
            prompt=prompt,
            existing_name=existing_name,
            existing_constraints=existing_constraints_str,
            l1_skills_context=l1_skills_context,
            scan_target=scan_target,
            output_dir=output_dir,
            existing_design_file_path=existing_design_file_path
        )

        try:
            skeleton_text = gemini_client.generate_design(contents=l1_request, response_schema=SkeletonDesign)
            # LLM出力から markdown 修飾などを除去
            if "```" in skeleton_text:
                skeleton_text = "\n".join([line for line in skeleton_text.split("\n") if not line.strip().startswith("```")])
            skeleton_design = json.loads(skeleton_text)
        except Exception as e:
            return Output(status="failed", message=f"第一段階（L1粗設計）生成またはパースエラー: {e}", output_dir="")

        # 5. 第 2 段階 (L2引数マッピング)
        # 骨組みで選ばれた依存スキルの詳細スキーマをオンデマンドでロード
        l2_elements = []
        steps = skeleton_design.get("steps", [])
        if steps and isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("type") == "skill":
                    target_skill = step.get("target")
                    if target_skill:
                        try:
                            dep_skill = state.get_skill(target_skill)
                            dep_design = dep_skill.load_design()
                            
                            inputs_def = []
                            for p in dep_design.parameters:
                                inputs_def.append(f"    * {p.name} ({p.type}) {'(必須)' if p.required else '(任意)'}: {p.description}")
                            inputs_def_str = "\n".join(inputs_def) if inputs_def else "    なし"
                            
                            outputs_def = []
                            if dep_design.response_parameters:
                                for p in dep_design.response_parameters:
                                    outputs_def.append(f"    * {p.name} ({p.type}): {p.description}")
                            outputs_def_str = "\n".join(outputs_def) if outputs_def else "    なし"

                            l2_elements.append(
                                f"■ スキル名: {dep_design.name}\n"
                                f"  説明: {dep_design.description}\n"
                                f"  入力パラメータ仕様:\n{inputs_def_str}\n"
                                f"  出力戻り値仕様:\n{outputs_def_str}\n"
                            )
                        except Exception as e:
                            # 依存スキルの設計ロード失敗時は警告しつつスキップ
                            print(f"Warning: Failed to load design for {target_skill}: {e}")

        l2_skills_context = "\n".join(l2_elements) if l2_elements else "なし"

        # デバッグ出力

        # L2 (引数マッピング/精緻化) 用リクエストの作成
        l2_request = design_prompter.build_l2_request(
            client=gemini_client._client,
            skeleton_design_str=json.dumps(skeleton_design, indent=2, ensure_ascii=False),
            l2_skills_context=l2_skills_context
        )

        # L2 呼び出し: 最終設計の生成
        try:
            response_text = gemini_client.generate_design(contents=l2_request, response_schema=ModuleDesign)
            if "```" in response_text:
                response_text = "\n".join([line for line in response_text.split("\n") if not line.strip().startswith("```")])
            design_data = json.loads(response_text)
        except Exception as e:
            return Output(status="failed", message=f"第二段階（L2引数マッピング）生成またはパースエラー: {e}", output_dir="")

        # パースされたデータの決定論的な自動補正
        design_data = DesignCleanser().clean(design_data)

        # 概要 (summary) フィールドの処理
        # ユーザーから明示的な summary が指定されている場合は、それを最優先で上書き
        if summary_override:
            design_data["summary"] = summary_override

        # 5.5. Pydantic モデルによるスキーマバリデーション (スキルとワークフローの切り分けチェック)
        try:
            TypeAdapter(ModuleDesign).validate_python(design_data)
        except Exception as e:
            return Output(
                status="failed", 
                message=f"設計データのバリデーションエラー（スキルとワークフローの構成不整合など）: {e}", 
                output_dir=""
            )

        output_file_path = skill_directory.design_path
        assets_dir = os.path.dirname(output_file_path)
        
        try:
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(design_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return Output(status="failed", message=f"design.json の保存エラー: {e}", output_dir="")

        message = f"design.json が '{output_file_path}' に正常に生成されました。"
        return Output(status="success", message=message, output_dir=output_dir)