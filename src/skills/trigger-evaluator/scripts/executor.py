import os
import sys
import json
from google.adk.tools import ToolContext
from .models import Input, Output
from .evaluator import StaticEvaluator
from .generator import TriggerGenerator
from .asset_manager import AssetManager

class SkillExecutor:
    """ビジネスロジックを責務ごとに分割して実行するオブジェクト指向エグゼキューター。

    Args:
        params: 呼び出し元から渡された型安全な入力パラメータ。
        tool_context: ADKのセッション状態などを管理するコンテキスト。
    """

    def __init__(self, params: Input, tool_context: ToolContext):
        """SkillExecutor を初期化します。"""
        self.params = params
        self.tool_context = tool_context

        # パッケージ初期ロード時の循環参照を回避するため、実行時に遅延ローカルインポート
        from edd_agent_tools.skills import SkillsState
        self.skills_state = SkillsState()

        # 各責務クラスのインスタンス化 (DI引数と状態保持を排除)
        self.static_evaluator = StaticEvaluator()
        self.trigger_generator = TriggerGenerator()
        self.asset_manager = AssetManager()

    def execute(self) -> Output:
        """ビジネスロジックを実行し、結果を返します。

        Returns:
            Output: 処理結果の構造化データ（Output）。

        Raises:
            RuntimeError: ロジック実行中にエラーが発生した場合。
            FileNotFoundError: 対象スキルが見つからない場合。
            ValueError: 入力パラメータが不正な場合。
        """
        skill_name = self.params.skill
        if not skill_name:
            raise ValueError("エラー: skill がパラメータに指定されていません。")

        try:
            target_dir = self.skills_state.get_skill(skill_name)
        except Exception as e:
            raise FileNotFoundError(f"対象スキル '{skill_name}' が見つかりません: {e}")

        print(f"スキル '{skill_name}' のトリガーアセット生成を開始します。\n")

        status = "success"
        message = "Successfully generated trigger test assets."
        eval_set_filepath = ""

        try:
            # SKILL.md のロード
            try:
                skill_md_content = target_dir.load_spec()
            except FileNotFoundError as e:
                raise FileNotFoundError(f"対象スキル '{skill_name}' のSKILL.mdファイルが見つかりません: {e}")

            # 第1ゲート: 静的評価
            static_eval_result = self.static_evaluator.evaluate(skill_name, skill_md_content)
            if not static_eval_result["passed"]:
                raise RuntimeError(f"トリガー静的評価不合格 (Specificity: {static_eval_result.get('specificity')}, Clarity: {static_eval_result.get('clarity')})\nフィードバック: {static_eval_result.get('feedback')}")

            # 第2ゲート: テストケース生成
            eval_cases = self.trigger_generator.generate(skill_name, skill_md_content)
            if not eval_cases:
                raise RuntimeError("テストケース生成に失敗しました。")

            # アセット保存
            eval_set_filepath = self.asset_manager.save_eval_assets(skill_name, eval_cases, target_dir)
            if not eval_set_filepath:
                raise RuntimeError("評価アセットの保存に失敗しました。")

            # 全体合格とレポート保存
            print(f"🎉 スキル '{skill_name}' のトリガー評価用テストアセットを正常に生成しました！")
            self.asset_manager.save_report(skill_name, static_eval_result, eval_set_filepath, target_dir)
            print("アセット生成プロセスが正常に完了しました。")

        except Exception as e:
            status = "failed"
            message = str(e)
            print(f"❌ エラー: {e}", file=sys.stderr)

        # 共通の出力状態のセット
        self.tool_context.state.update({
            "status": status,
            "message": message,
            "eval_set_path": eval_set_filepath
        })

        if status == "success":
            self.tool_context.state["trig_eval_set_path"] = eval_set_filepath
            # ワークフロー用の固固有時フォルダへの書き出し (互換性のため)
            output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/05_trig_gen_out.json"
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "eval_set_path": eval_set_filepath
                }, f, indent=2, ensure_ascii=False)
        else:
            raise RuntimeError(message)

        return Output(value=message)
