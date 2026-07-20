import os
import json
from .models import SkillDesignerOutput
from pydantic import TypeAdapter
from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools import ModuleDesign
from .client import GeminiDesignClient
from .prompter import DesignPrompter
from .resolver import PathResolver
from .parser import ConstraintParser
from .cleanser import DesignCleanser
from .skeleton_models import SkeletonDesign
from google.genai import types 

class SkillExecutor:
    """
    自然言語の要件や既存のソースコードから ADK 2.0 互換の design.json を設計して出力する
    オブジェクト指向エグゼキューター。
    """
    def __init__(self):
        """
        SkillExecutor のコンストラクタ。
        このクラスは状態を持たず、メソッド呼び出し時に必要な引数を受け取る設計とする。
        """
        self._path_resolver = PathResolver()
        self._constraint_parser = ConstraintParser()
        self._gemini_client = GeminiDesignClient()
        self._state = SkillsState()

    def skill_designer(self, prompt: str, summary: str = None, output_dir: str = None, skill: str = None, source_code_dir: str = None, target_entry: str = None) -> SkillDesignerOutput:
        """
        スキル設計のメインロジックを実行します。

        Args:
            prompt: 設計するスキルの機能要件や追加の改修要望を記述した自然言語のテキスト。
            summary: スキルの仕様概要（ビジネス目的や要求の要約）。指定した場合、Geminiによる自動要約より優先して design.json の summary フィールドに保存されます。
            output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。省略時はskillから自動探索されます。
            skill: 既存のスキル名。再設計時の自動探索キーとして使用されます。
            source_code_dir: 再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。指定しない場合、自動的に検出を試みます。
            target_entry: 優先する論理配置先名。

        Returns:
            処理結果のOutputオブジェクト。
        """
        # 1. パス解決
        resolved_paths = self._path_resolver.resolve_paths(skill_name=skill, output_dir=output_dir, source_code_dir=source_code_dir, target_entry=target_entry)
        
        existing_name = resolved_paths["existing_name"]
        output_dir = resolved_paths["output_dir"] # 解決されたパスで更新
        scan_target = resolved_paths["scan_target"]
        skill_directory = resolved_paths["skill_directory"]

        # 2. 既存の制約事項を抽出
        existing_constraints_str = self._constraint_parser.get_existing_constraints(existing_name)

        # 3. DesignPrompter の初期化
        designer_skill = self._state.get_skill("skill-designer")
        design_prompter = DesignPrompter(designer_skill=designer_skill)
        
        output_file_path = skill_directory.design_path
        existing_design_file_path = output_file_path if os.path.exists(output_file_path) else None

        # 4. L1 (粗設計/骨組み) 用リクエストの作成と生成
        l1_request = self._build_l1_request(
            design_prompter=design_prompter,
            prompt=prompt,
            existing_name=existing_name,
            existing_constraints=existing_constraints_str,
            scan_target=scan_target,
            output_dir=output_dir,
            existing_design_file_path=existing_design_file_path
        )

        try:
            skeleton_design = self._generate_design(l1_request)
        except Exception as e:
            return SkillDesignerOutput(status="failed", message=f"第一段階（L1粗設計）生成またはパースエラー: {e}", output_dir="")

        # 5. 第 2 段階 (L2引数マッピング・精緻化)
        # L2 (パラメータ精緻化) 用リクエストの作成
        l2_request = design_prompter.build_l2_request(
            client=self._gemini_client._client,
            skeleton_design_str=json.dumps(skeleton_design, indent=2, ensure_ascii=False)
        )

        # L2 呼び出し: 最終設計の生成
        try:
            design_data = self._generate_design(l2_request, summary_override=summary)
        except Exception as e:
            return SkillDesignerOutput(status="failed", message=f"第二段階（L2パラメータ精緻化）生成またはパースエラー: {e}", output_dir="")

        # 5.5. Pydantic モデルによるスキーマバリデーション (スキルとワークフローの切り分けチェック)
        try:
            TypeAdapter(ModuleDesign).validate_python(design_data)
        except Exception as e:
            return SkillDesignerOutput(
                status="failed", 
                message=f"設計データのバリデーションエラー（スキルとワークフローの構成不整合など）: {e}", 
                output_dir=""
            )

        # 6. design.json の保存
        try:
            self._save_design(design_data, skill_directory.design_path, output_dir)
        except Exception as e:
            return SkillDesignerOutput(status="failed", message=f"design.json の保存エラー: {e}", output_dir="")

        message = f"design.json が '{skill_directory.design_path}' に正常に生成されました。"
        return SkillDesignerOutput(status="success", message=message, output_dir=output_dir)

    def _build_l1_request(
        self, 
        design_prompter: DesignPrompter,
        prompt: str, 
        existing_name: str | None, 
        existing_constraints: str, 
        scan_target: str | None,
        output_dir: str | None,
        existing_design_file_path: str | None = None
    ) -> types.GenerateContentRequest:
        """L1設計用のリクエストを構築します。"""
        # 4.1. L1メタデータの収集（全登録スキルの名前とトリガー説明）
        l2_elements = []
        discovered_skills = self._state.scan_skills()
        for target_skill, skill_obj in discovered_skills.items():
            try:
                dep_design = skill_obj.load_design()
                inputs_def = []
                outputs_def = []
                
                if getattr(dep_design, 'functions', None):
                    for fn in dep_design.functions:
                        inputs_def.append(f"  - 関数 {fn.name} の入力:")
                        for p in fn.parameters:
                            inputs_def.append(f"    * {p.name} ({p.type}) {'(必須)' if p.required else '(任意)'}: {p.description}")
                        if fn.response_parameters:
                            outputs_def.append(f"  - 関数 {fn.name} の出力:")
                            for p in fn.response_parameters:
                                outputs_def.append(f"    * {p.name} ({p.type}): {p.description}")
                elif getattr(dep_design, 'parameters', None):
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

    def _generate_design(self, request: types.GenerateContentRequest, summary_override: str | None = None) -> dict:
        """設計仕様（L1粗設計またはL2詳細設計）をGeminiから生成し、クレンジングを適用して返します。"""
        response_text = self._gemini_client.generate_design(contents=request, response_schema=ModuleDesign)
        if "```" in response_text:
            response_text = "\n".join([line for line in response_text.split("\n") if not line.strip().startswith("```")])
        
        design_data = json.loads(response_text)
        
        # パースされたデータの決定論的な自動補正
        design_data = DesignCleanser().clean(design_data)

        # 概要 (summary) フィールドの処理
        # ユーザーから明示的な summary が指定されている場合は、それを最優先で上書き
        if summary_override:
            design_data["summary"] = summary_override
            
        return design_data

    def _save_design(self, design_data: dict, design_file_path: str, output_dir: str):
        """設計データをファイルに保存します。"""
        assets_dir = os.path.dirname(design_file_path)
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        with open(design_file_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, indent=2, ensure_ascii=False)

        # 設計保存後に、プロジェクト全体の依存整合性（欠落・循環参照）を動的にチェックする（ハーネス）
        try:
            self._state.validate_dependencies()
        except ValueError as e:
            # 循環依存などのエラーが発生した場合は警告を表示してフィードバックする
            print(f"⚠️ 警告: 依存関係検証エラーが検出されました:\n{e}")