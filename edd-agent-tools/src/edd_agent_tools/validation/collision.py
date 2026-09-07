"""
Semantic Collision Detector (Clarity Gate)

白書 Section 4 (Page 22)「The trigger is the first gate: Clarity: Ambiguous queries don't overlap with adjacent skills」準拠：
登録されている全エージェントスキルの Frontmatter Description 間の重複・意味的競合を
決定論的テキスト解析（N-gram Jaccard / 単語頻度コサイン類似度）により検知し、
誤爆やルーティング曖昧性を防止するチェッカー。
"""

import re
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from edd_agent_tools.state import SkillsState


def _tokenize(text: str) -> List[str]:
    """英語および日本語の簡易トークン分割"""
    words = re.findall(r"[a-zA-Z0-9_\-]+|[一-龥ぁ-んァ-ン]+", text.lower())
    stopwords = {"and", "or", "the", "a", "an", "is", "in", "to", "for", "with", "of", "on", "when", "use", "this", "skill", "user", "asks"}
    return [w for w in words if len(w) > 1 and w not in stopwords]


def _compute_jaccard_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """トークン集合の Jaccard 類似度"""
    s1, s2 = set(tokens1), set(tokens2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _compute_cosine_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """単語頻度ベクトルのコサイン類似度"""
    c1, c2 = Counter(tokens1), Counter(tokens2)
    dot = sum(c1[t] * c2[t] for t in c1 if t in c2)
    norm1 = math.sqrt(sum(v * v for v in c1.values()))
    norm2 = math.sqrt(sum(v * v for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticCollisionDetector:
    """全スキルの Description 間の重複・衝突を検知するクラス。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()

    def detect_collisions(
        self,
        target_skill_name: Optional[str] = None,
        threshold: float = 0.60
    ) -> List[Dict[str, Any]]:
        """全スキル（または対象スキルと他スキル）の類似度を計算し、閾値を超える衝突候補を返却します。"""
        skills = self.state.scan_skills()
        skill_descriptions = {name: s.description for name, s in skills.items() if s.description}

        collisions = []
        names = sorted(list(skill_descriptions.keys()))

        for i in range(len(names)):
            name1 = names[i]
            if target_skill_name and name1 != target_skill_name:
                continue
            desc1 = skill_descriptions[name1]
            tokens1 = _tokenize(desc1)

            for j in range(i + 1, len(names)):
                name2 = names[j]
                desc2 = skill_descriptions[name2]
                tokens2 = _tokenize(desc2)

                jaccard = _compute_jaccard_similarity(tokens1, tokens2)
                cosine = _compute_cosine_similarity(tokens1, tokens2)
                composite_sim = (cosine * 0.7) + (jaccard * 0.3)

                if composite_sim >= threshold:
                    collisions.append({
                        "skill_1": name1,
                        "skill_2": name2,
                        "similarity": round(composite_sim, 3),
                        "cosine": round(cosine, 3),
                        "jaccard": round(jaccard, 3),
                        "common_keywords": sorted(list(set(tokens1) & set(tokens2)))[:8]
                    })

        return sorted(collisions, key=lambda x: x["similarity"], reverse=True)
