import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from edd_agent_tools.skills import SkillsState, Skill, SkillValidator, SkillTier
from edd_agent_tools.evaluation import CascadeTestRunner
from edd_agent_tools.gemini import client, GeminiRequest


class SkillOptimizer:
    """テスト失敗検知 ➔ 診断 ➔ 3層リソース差分修正 ➔ 再テスト ➔ 連鎖回帰テストの自律改善ループエンジン。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.cascade_runner = CascadeTestRunner(self.state)
        self._client = client

    def optimize_skill(
        self,
        skill_name: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """指定されたスキルの自律改善ループを実行します。

        Args:
            skill_name: 改善対象のスキル名。
            max_retries: 最大修正試行回数。

        Returns:
            Dict[str, Any]: 改善結果サマリー。
        """
        skill = self.state.get_skill(skill_name)
        if not skill or not os.path.exists(skill.root_dir):
            return {"status": "failed", "message": f"Skill '{skill_name}' not found or directory does not exist."}

        print(f"\n=======================================================")
        print(f"🚀 [SkillOptimizer] スキル '{skill_name}' の自律改善ループを開始します。")
        print(f"=======================================================\n")

        for attempt in range(1, max_retries + 1):
            print(f"\n--- [Iteration {attempt}/{max_retries}] 診断・修復サイクル ---")

            # 1. 静的バリデーション
            val_res = SkillValidator.validate_directory(skill.root_dir)
            if not val_res.is_valid:
                print(f"⚠️ 静的リンター警告/エラー: {val_res.errors}")

            # 2. 診断の実行 (skill-diagnoser)
            diag_skill = self.state.get_skill("skill-diagnoser")
            diag_output = None
            if diag_skill:
                mod = diag_skill.load_module()
                if hasattr(mod, "SkillExecutor"):
                    diagnoser = mod.SkillExecutor(skill=skill_name)
                    diag_output = diagnoser.execute()
                elif hasattr(mod, "diagnose_skill_failure"):
                    res = mod.diagnose_skill_failure(skill=skill_name)
                    # res is DiagnoseSkillFailureOutput
                    diag_output = res

            if diag_output.status != "success" or not diag_output.plan:
                print(f"❌ 診断の実行に失敗しました: {diag_output.details}")
                # レポートが存在しないか全合格の場合
                if diag_output.plan and diag_output.plan.verdict == "no_issues_found":
                    print("✅ 修復すべき問題は検出されませんでした（全テスト合格状態）。")
                    break
                # レポートがない場合は初期テスト合格とみなすか終了
                break

            plan = diag_output.plan
            print(f"📋 診断結果: verdict={plan.verdict}, layer={plan.target_layer.value}, category={plan.failure_category.value}")
            print(f"🔍 根本原因: {plan.root_cause}")

            if plan.verdict == "no_issues_found":
                print("🎉 すべてのテストが合格しました！")
                break

            # 3. 差分パッチの適用
            applied = self._apply_improvement_plan(skill, plan)
            if not applied:
                print("⚠️ パッチの適用に失敗しました。")
            else:
                print("🛠 パッチが正常に適用されました。")

            # 4. パッチ後の静的検証
            post_val = SkillValidator.validate_directory(skill.root_dir)
            if not post_val.is_valid:
                print(f"⚠️ パッチ適用後の静的リンターエラー: {post_val.errors}")

        # 5. 連鎖回帰テストの実行
        print(f"\n🔗 [Cascade Testing] 上位ワークフローへの連鎖回帰テストを実行中...")
        cascade_res = self.cascade_runner.run_cascade_tests(skill_name)
        
        if cascade_res["all_passed"]:
            print(f"✅ 連鎖回帰テスト合格 (検証対象上位スキル: {cascade_res['dependents_count']}件)")
            # Tier 1 昇格
            skill.set_tier(SkillTier.READ_ONLY)
            self.state.register_skill(skill)
            return {
                "status": "success",
                "skill": skill_name,
                "tier": "READ_ONLY (Tier 1)",
                "cascade_results": cascade_res,
                "message": f"スキル '{skill_name}' の自己修復・最適化が正常に完了し、Tier 1 へ昇格しました。"
            }
        else:
            print(f"❌ 連鎖回帰テストで不備が検出されました: {cascade_res['results']}")
            return {
                "status": "partial_success",
                "skill": skill_name,
                "tier": "SANDBOX (Tier 0)",
                "cascade_results": cascade_res,
                "message": f"スキル自体の修復は試行されましたが、上位ワークフローの連鎖テストで不整合が検出されました。"
            }

    def _apply_improvement_plan(self, skill: Skill, plan: Any) -> bool:
        """ImprovementPlan の内容に従ってファイルへパッチを適用します。"""
        try:
            target_layer = plan.target_layer.value

            # A. スクリプト層の修正 (scripts/*.py)
            if target_layer == "script" and plan.script_patch:
                patch = plan.script_patch
                target_path = os.path.join(skill.root_dir, patch.target_file)
                
                if patch.suggested_code and os.path.exists(target_path):
                    with open(target_path, "r", encoding="utf-8") as f:
                        current_code = f.read()

                    # 単純置換またはLLMによるコード修復
                    if patch.problematic_code_snippet and patch.problematic_code_snippet in current_code:
                        new_code = current_code.replace(patch.problematic_code_snippet, patch.suggested_code)
                    else:
                        # LLM を用いて安全にマージ
                        merge_prompt = f"""以下のPythonコードに対し、指定された修正指示を適用した完全なコードを出力してください。

【対象ファイル】
{patch.target_file}

【既存コード】
```python
{current_code}
```

【修正指示】
{patch.fix_instructions}

【推奨修正スニペット】
```python
{patch.suggested_code}
```

Markdownの ```python ... ``` コードブロックで囲んで完全なPythonコードのみを出力してください。
"""
                        req = GeminiRequest(prompt=merge_prompt, client=self._client)
                        res = req.execute()
                        text = res.text if hasattr(res, "text") else str(res)
                        match = re.search(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL)
                        new_code = match.group(1).strip() if match else text.strip()

                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(new_code)
                    print(f"  Applied script patch to {patch.target_file}")
                    return True

            # B. 仕様層の修正 (SKILL.md)
            elif target_layer == "spec" and plan.spec_patch:
                patch = plan.spec_patch
                if patch.description_patch and os.path.exists(skill.spec_path):
                    with open(skill.spec_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # description の置換
                    new_content = re.sub(
                        r'description:\s*".*?"',
                        f'description: "{patch.description_patch}"',
                        content
                    )
                    with open(skill.spec_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"  Applied spec patch to SKILL.md")
                    return True

            return False

        except Exception as e:
            print(f"Error applying improvement plan: {e}")
            return False
