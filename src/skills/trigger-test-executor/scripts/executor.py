import os
import json
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from edd_agent_tools.evaluation import EvalRunResult, TrajectoryEvalSet

class SkillExecutor:
    """トリガー（インテント）評価テストを実行し、その結果を検証するクラス。"""

    def __init__(self):
        self._skills_state = SkillsState()
        self._gemini_client = GeminiClient()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """トリガー（インテント）評価テストを実行し、その結果を検証します。

        Args:
            skill_name: 評価対象となるスキルの名前。
            eval_set_path: TrajectoryEvalSet形式のJSONファイルへのパス。
            env: ワークスペース環境プロトコル。

        Returns:
            テスト実行結果オブジェクト (EvalRunResult)。
        """
        try:
            # 1. 評価セットのロードとパース
            with open(eval_set_path, "r", encoding="utf-8") as f:
                eval_set_data = json.load(f)
            eval_set = TrajectoryEvalSet.model_validate(eval_set_data)

            # 2. ワークスペース内のすべてのスキル仕様情報を構築
            all_skills = self._skills_state.list_skills()
            skills_info = {}
            for skill in all_skills:
                try:
                    spec_content = skill.load_spec()
                    skills_info[skill.name] = spec_content
                except Exception:
                    pass

            # スキル一覧プロンプトテキストの構築
            skills_list_parts = []
            for name, spec in skills_info.items():
                skills_list_parts.append(f"### スキル名: {name}\n仕様定義:\n{spec}\n")
            skills_list_formatted = "\n".join(skills_list_parts)

            passed_count = 0
            failed_count = 0
            detailed_results = []

            # 3. 各テストケースを実行
            for case in eval_set.eval_cases:
                for turn in case.conversation:
                    # ユーザーの発話プロンプト
                    user_utterance = turn.user_content.get("parts", [{}])[0].get("text", "")
                    if not user_utterance:
                        continue

                    # 期待値の判定
                    # tool_uses があれば positive (期待されるのは対象の skill_name)
                    # なければ negative (期待されるのは "None")
                    if turn.intermediate_data.tool_uses:
                        tool_use = turn.intermediate_data.tool_uses[0]
                        # args.params.skill から直接スキル名を取得するか、tool_use.name から逆引
                        expected_skill = tool_use.args.get("params", {}).get("skill", skill_name)
                    else:
                        expected_skill = "None"

                    # 4. LLM による予測分類
                    predicted_skill = self._predict_intent(
                        user_utterance=user_utterance,
                        skills_list_formatted=skills_list_formatted
                    )

                    # 5. 合否判定
                    is_positive_case = (expected_skill == skill_name)
                    if is_positive_case:
                        is_passed = (predicted_skill == skill_name)
                    else:
                        is_passed = (predicted_skill != skill_name)

                    if is_passed:
                        passed_count += 1
                    else:
                        failed_count += 1

                    detailed_results.append({
                        "case_id": case.eval_id,
                        "user_prompt": user_utterance,
                        "expected": expected_skill,
                        "predicted": predicted_skill,
                        "status": "PASSED" if is_passed else "FAILED"
                    })

            total_count = passed_count + failed_count
            accuracy = (passed_count / total_count) if total_count > 0 else 1.0

            # 6. 詳細結果の書き出し
            target_skill = self._skills_state.get_skill(skill_name)
            tests_dir = os.path.join(target_skill.root_dir, "tests")
            os.makedirs(tests_dir, exist_ok=True)
            detail_file_path = os.path.join(tests_dir, f"{skill_name.replace('-', '_')}_trigger_detail.json")
            
            with open(detail_file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "skill": skill_name,
                    "accuracy": accuracy,
                    "results": detailed_results
                }, f, indent=2, ensure_ascii=False)

            return EvalRunResult(
                passed=passed_count,
                failed=failed_count,
                total=total_count,
                accuracy=accuracy,
                detail_file_path=detail_file_path
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return EvalRunResult(
                passed=0,
                failed=1,
                total=1,
                accuracy=0.0,
                detail_file_path=None
            )

    def _predict_intent(self, user_utterance: str, skills_list_formatted: str) -> str:
        """Gemini API を呼び出してインテント分類を行い、スキル名または 'None' を返します。"""
        prompt = f"""あなたは高度なADKエージェントルーターです。
ユーザーの入力プロンプトに対して、どのツール（スキル）を呼び出すべきかを選択してください。

## 選択肢（スキル一覧）:
{skills_list_formatted}
- 'None': どのスキル（ツール）にも該当しない場合、または判断できない場合。

## ユーザー入力:
"{user_utterance}"

## 判定ルール:
1. ユーザーの入力内容が、スキルの役割やパラメータ定義に合致しているかを各スキルの仕様書（SKILL.md）を参考に判断してください。
2. 最も適切と思われるスキル名を1つだけ選択して返してください。
3. どのスキルにも当てはまらない、または他愛のない会話（挨拶など）である場合は、'None' と返してください。
4. 出力は、選択したスキル名（例: 'my-skill'）または 'None' のみとし、他の説明や文字は一切含めないでください。
"""
        response = self._gemini_client.request(prompt).execute()
        result = response.text.strip().replace("'", "").replace('"', "")
        return result
