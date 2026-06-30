import sys
# インポート不整合対策
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

import pathlib

# security モジュールのインポート
sys.path.append("/workspace/src/skills/skill-manager/scripts")
import security

# 1. 許可されているツールのテスト
allowed = security.get_allowed_tools_for_skill("test-skill")
print("Allowed tools for test-skill (Tier 2):", allowed)
assert "write_file" in allowed
assert "execute" not in allowed

# 2. SkillToolset の動的生成テスト
from google.adk.skills import models
mock_skill = models.Skill(
    frontmatter=models.Frontmatter(name="test-skill", description="test"),
    instructions="Test instructions."
)
toolset = security.create_secure_skill_toolset(mock_skill)

# 3. EnvironmentToolset の動的生成テスト
from google.adk.environment import LocalEnvironment
env = LocalEnvironment()
env_toolset = security.create_secure_environment_toolset("test-skill", env)

# 非同期 get_tools の実行
import asyncio
async def test_tools():
    # SkillToolset tools
    skill_tools = await toolset.get_tools()
    skill_tool_names = [t.name for t in skill_tools if toolset._is_tool_selected(t, None)]
    print("SkillToolset tools:", skill_tool_names)
    assert any("load_skill" in name.lower() for name in skill_tool_names)
    assert not any("run_skill_script" in name.lower() for name in skill_tool_names)

    # EnvironmentToolset tools
    env_tools = await env_toolset.get_tools()
    env_tool_names = [t.name for t in env_tools]
    print("Filtered environment tools (Tier 2):", env_tool_names)
    # 正規化してアサーション
    norm_names = [name.replace("_", "").lower() for name in env_tool_names]
    assert "writefile" in norm_names
    assert "execute" not in norm_names
    print("Security library works perfectly!")

asyncio.run(test_tools())
