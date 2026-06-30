"""
Google ADK の Toolset に対し、スキルのTierに基づいた安全なツールフィルタリング（権限隔離）を提供するモジュール。
"""
import json
import pathlib
from google.adk.tools import skill_toolset
from google.adk.tools.environment import EnvironmentToolset

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
# /workspace/src/skills/skill-manager/scripts -> /workspace/src/skills_registry.json
REGISTRY_PATH = SCRIPT_DIR.parent.parent.parent / "skills_registry.json"
POLICY_PATH = SCRIPT_DIR.parent / "assets" / "policy.json"

class FilteredEnvironmentToolset(EnvironmentToolset):
    """EnvironmentToolset のバグ（tool_filter が get_tools 内で適用されない問題）を修正し、
    かつキャメルケース・スネークケースの表記揺れを許容して正しくツールをフィルタリングするラッパークラス。
    """
    async def get_tools(self, readonly_context=None):
        # 親クラスの get_tools を呼び出して全ツールを取得
        all_tools = await super().get_tools(readonly_context)
        if not self.tool_filter:
            return all_tools
            
        # フィルターの値を小文字＆アンダースコア除去で正規化
        normalized_filter = [t.replace("_", "").lower() for t in self.tool_filter]
        
        filtered = []
        for tool in all_tools:
            norm_name = tool.name.replace("_", "").lower()
            if norm_name in normalized_filter:
                filtered.append(tool)
        return filtered

def get_allowed_tools_for_skill(skill_name: str) -> list[str]:
    """レジストリとポリシーから、対象スキルに許可されているツール名のリストを取得します。"""
    # 1. registry からスキルの現在の Tier を取得
    tier = "1"  # デフォルトは最も厳しい Tier 1
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry = json.load(f)
            tier = str(registry.get("skills", {}).get(skill_name, {}).get("tier", 1))
        except Exception:
            pass

    # 2. policy.json から許可ツールを取得
    allowed = []
    if POLICY_PATH.exists():
        try:
            with open(POLICY_PATH, "r", encoding="utf-8") as f:
                policy = json.load(f)
            allowed = policy.get("tiers", {}).get(tier, {}).get("allowed_tools", [])
        except Exception:
            pass
            
    if not allowed:
        # フォールバック (Tier 1 相当)
        allowed = [
            "read_file", "list_dir", "view_file",
            "load_skill", "load_skill_resource", "list_skills"
        ]

    return allowed

def create_secure_skill_toolset(skill, code_executor=None, **kwargs):
    """対象スキルのTierに基づき、利用可能なツールを制限した SkillToolset を返します。"""
    allowed_tools = get_allowed_tools_for_skill(skill.name)
    
    if "*" in allowed_tools:
        tool_filter = None
    else:
        # SkillToolset で提供されうるツールのリスト
        possible_tools = ["load_skill", "load_skill_resource", "run_skill_script", "list_skills"]
        tool_filter = [t for t in possible_tools if t in allowed_tools]
        
    return skill_toolset.SkillToolset(
        skills=[skill],
        code_executor=code_executor,
        tool_filter=tool_filter,
        **kwargs
    )

def create_secure_environment_toolset(skill_name: str, environment, **kwargs):
    """対象スキルのTierに基づき、利用可能なツールを制限した EnvironmentToolset を返します。"""
    allowed_tools = get_allowed_tools_for_skill(skill_name)
    
    if "*" in allowed_tools:
        tool_filter = None
    else:
        # EnvironmentToolset で提供されうるツールのリスト
        possible_tools = ["execute", "read_file", "edit_file", "write_file"]
        tool_filter = [t for t in possible_tools if t in allowed_tools]
        
    return FilteredEnvironmentToolset(
        environment=environment,
        tool_filter=tool_filter,
        **kwargs
    )
