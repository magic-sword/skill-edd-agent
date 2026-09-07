"""
Agent Card Synchronizer for A2A v1.0.0 & Agent Registry

SkillsState から Tier 1 以上の全スキル情報を集約し、
A2A v1.0.0 仕様（supportedInterfaces 配列、MIME types、examples 等）に
完全準拠した agent-card.json を動的に生成・同期します。
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from edd_agent_tools.state import SkillsState
from edd_agent_tools.models.state import SkillTier


class AgentCardSynchronizer:
    """A2A v1.0.0 互換の Agent Card を自動生成・同期するクラス。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()

    def generate_agent_card(
        self,
        name: str = "evaluation_driven_development_agent",
        description: str = "Google ADK 2.0 と Anthropic スキル標準に完全準拠した自己進化型評価駆動開発エージェント",
        version: str = "1.0.0",
        port: int = 8001,
        min_tier: int = 1
    ) -> Dict[str, Any]:
        """Tier min_tier 以上の全スキルを抽出し、A2A v1.0.0 の Agent Card 辞書を構築します。"""
        discovered = self.state.scan_skills()
        skills_entries = []

        for skill_name, skill_obj in sorted(discovered.items()):
            # Tier フィルタリング (システムスキルは常に含める)
            t_val = skill_obj.tier.value if hasattr(skill_obj.tier, "value") else int(skill_obj.tier or 0)
            is_system = skill_name in {"skill-creator", "skill-evolver", "skill-reviewer"}
            if t_val < min_tier and not is_system:
                continue

            # Frontmatter 情報
            spec = skill_obj.spec
            desc = spec.description if spec else f"Execute {skill_name} skill"

            # Examples の抽出
            examples: List[str] = []
            if spec and hasattr(spec, "body") and spec.body:
                ex_match = re.search(r"##\s+Examples\s*\n+(.*?)(?=\n##|\Z)", spec.body, re.DOTALL | re.IGNORECASE)
                if ex_match:
                    lines = [line.strip().lstrip("-*•").strip() for line in ex_match.group(1).splitlines() if line.strip().startswith(("-", "*", "•"))]
                    examples.extend(lines[:3])

            if not examples:
                # tests/*.test.json から代表的な user_input を抽出
                try:
                    evalset_path = skill_obj.tests.get_evalset_path("composite") or skill_obj.tests.get_evalset_path("trigger")
                    if evalset_path and Path(evalset_path).exists():
                        with open(evalset_path, "r", encoding="utf-8") as f:
                            tdata = json.load(f)
                            for c in tdata.get("eval_cases", [])[:3]:
                                if isinstance(c, dict):
                                    conv = c.get("conversation", [])
                                    if conv and "user_content" in conv[0]:
                                        parts = conv[0]["user_content"].get("parts", [])
                                        if parts and "text" in parts[0]:
                                            examples.append(parts[0]["text"])
                except Exception:
                    pass

            tags = ["llm", "tools", f"tier-{t_val}"]
            if spec and hasattr(spec, "metadata") and isinstance(spec.metadata, dict):
                pattern = spec.metadata.get("pattern")
                if pattern:
                    tags.append(str(pattern))

            skills_entries.append({
                "id": f"{name}-{skill_name}",
                "name": skill_name,
                "description": desc.strip().replace("\n", " "),
                "tags": tags,
                "examples": examples
            })

        card = {
            "name": name,
            "description": description,
            "version": version,
            "supportedInterfaces": [
                {
                    "url": f"http://localhost:{port}",
                    "protocolBinding": "HTTP+JSON",
                    "protocolVersion": "1.0.0"
                }
            ],
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "extendedAgentCard": False
            },
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "skills": skills_entries
        }
        return card

    def sync_to_file(self, target_path: Optional[Path | str] = None, **kwargs) -> Path:
        """Agent Card を生成し、ファイルへ書き出します。"""
        dest = Path(target_path).resolve() if target_path else Path("src/agent-card.json").resolve()
        card_data = self.generate_agent_card(**kwargs)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(card_data, f, ensure_ascii=False, indent=2)
        return dest
