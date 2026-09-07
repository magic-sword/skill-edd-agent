"""
Human-in-the-Loop Review Auditor (HumanReviewAuditor)

Google 『Agent Skills』ホワイトペーパー（May 2026）Section 6 (p.37-38, Figure 10) 準拠：
エージェントが自律的に作成・自己修復したスキルについて、
テスト指標への過学習（Gaming）や未知の回帰を人間が 30 秒で迅速に審査・承認（Sign-off）できるよう、
Git diff、静的検証、衝突検知スコア、およびテスト結果を包含した人間向け Markdown 監査レポートを自動生成するツール。
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

from edd_agent_tools.state import SkillsState
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.validation.collision import SemanticCollisionDetector


class HumanReviewAuditor:
    """人間による監査・Sign-off を支援するレポート生成クラス"""

    def __init__(self, workspace_root: Optional[Path] = None, state: Optional[SkillsState] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.state = state or SkillsState(project_root=self.workspace_root)
        self.collision_detector = SemanticCollisionDetector(state=self.state)

    def generate_audit_report(
        self,
        skill_name: str,
        output_path: Optional[Path] = None
    ) -> str:
        """指定されたスキルの監査レポート（Markdown）を生成します。"""
        skill = self.state.get_skill(skill_name)
        skill_dir = Path(skill.root_dir) if skill else (self.workspace_root / "src" / "skills" / skill_name)
        if not skill_dir.exists():
            skill_dir = self.workspace_root / ".agents" / "skills" / skill_name
            if not skill_dir.exists():
                raise ValueError(f"Skill directory for '{skill_name}' not found.")

        # 1. 静的検証結果の取得
        val_res = SkillValidator.validate_directory(skill_dir)

        # 2. 隣接スキルとの衝突判定
        collisions = self.collision_detector.detect_collisions(target_skill_name=skill_name, threshold=0.70)

        # 3. Git Diff の取得
        git_diff = "No Git changes detected."
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD~1", "--", str(skill_dir)],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.stdout.strip():
                git_diff = res.stdout.strip()
        except Exception:
            pass

        # 4. SKILL.md Frontmatter 情報
        skill_md = skill_dir / "SKILL.md"
        desc_text = "N/A"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("description:"):
                    desc_text = line.replace("description:", "").strip()
                    break

        tier = self.state.get_skill_tier(skill_name)

        report = f"""# 🛡️ Human-in-the-Loop Audit Report: `{skill_name}`

本書は、Google 『Agent Skills』ホワイトペーパー（May 2026）Section 6 準拠の人間承認（Human Sign-off）用監査レポートです。

---

## 1. スキル基本情報
- **Skill Name**: `{skill_name}`
- **Current Tier**: Tier {tier}
- **Location**: `{skill_dir.relative_to(self.workspace_root)}`
- **Description (Routing Algorithm)**:
  > {desc_text}

---

## 2. 決定論的静的検証 (SkillValidator)
- **判定**: {'✅ PASS (準拠)' if val_res.is_valid else '❌ FAIL (不適合)'}
- **エラー数**: {len(val_res.errors)} 件
- **警告数**: {len(val_res.warnings)} 件
"""
        if val_res.errors:
            report += "\n### エラー詳細\n"
            for err in val_res.errors:
                report += f"- ❌ {err}\n"

        report += f"""
---

## 3. 隣接スキル衝突検知 (Semantic Collision Check)
"""
        if collisions:
            report += f"⚠️ 類似度 0.70 以上の隣接スキルが {len(collisions)} 件検知されました：\n"
            for c in collisions:
                report += f"- `{c['skill_2']}`: 類似度 {c['similarity']:.1%} (重複キーワード: {', '.join(c.get('overlapping_terms', []))})\n"
        else:
            report += "✅ 近隣スキルとの意味的重複はありません（ルーティング競合なし）。\n"

        report += f"""
---

## 4. Git 変更差分 (Code & Instruction Diff)
```diff
{git_diff[:2000]}
```

---

## 5. 人間承認チェックリスト (Human Sign-off Checklist)
- [ ] 説明文（Description）が過度に特定のテストケースに過学習（Gaming）していないか？
- [ ] 意図しない負例クエリに誤発火するリスクはないか？
- [ ] 決定論的スクリプト（`scripts/`）にハードコードされた危険なパスや副作用はないか？

**承認判断**: `[ ] APPROVE (Tier 昇格)` / `[ ] REJECT / ROLLBACK`
"""

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")

        return report
