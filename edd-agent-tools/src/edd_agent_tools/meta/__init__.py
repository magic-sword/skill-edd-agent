"""
Meta-Skills and Evolutionary Capabilities for edd-agent-tools

Google 『Agent Skills』ホワイトペーパー (May 2026) Section 6 & 7 準拠：
- DescriptionOptimizer: Description Tuning Loop (Frontmatter 最適化)
- TraceHarvester: Authoring from Traces (実行軌跡からのスキル自律抽出)
- CapabilityProfileManager: Role-based Tool & Skill Bundling (Capability Profiles)
"""

from .description_optimizer import DescriptionOptimizer
from .trace_harvester import TraceHarvester
from .capability_profile import CapabilityProfile, CapabilityProfileManager

__all__ = [
    "DescriptionOptimizer",
    "TraceHarvester",
    "CapabilityProfile",
    "CapabilityProfileManager",
]
