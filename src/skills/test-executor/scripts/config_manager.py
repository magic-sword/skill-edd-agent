import os
import json
from edd_agent_tools.registry import SkillDirectory

class ConfigManager:
    def __init__(self, skill_directory: SkillDirectory):
        self._skill_directory = skill_directory

    def get_eval_config_path(self, eval_set_path: str) -> str:
        """
        テストファイルに対応する adk eval の設定ファイルパスを決定します。
        見つからない場合は、デフォルト設定ファイルを生成してそのパスを返します。
        """
        # パスの検証と絶対パス化
        if not os.path.isabs(eval_set_path):
            eval_set_path = os.path.abspath(os.path.join("/workspace", eval_set_path))
        
        if not os.path.exists(eval_set_path):
            raise FileNotFoundError(f"エラー: テストファイルが存在しません: {eval_set_path}")

        config_file = None

        # 1. テストファイル名に対応する config ファイル (例: [test_name].evalset.config.json) を確認
        if eval_set_path.endswith(".evalset.json"):
            possible_config = eval_set_path.replace(".evalset.json", ".evalset.config.json")
            if os.path.exists(possible_config):
                config_file = possible_config

        # 2. フォールバック: テストファイルがあるディレクトリ配下の一般的な設定名
        if not config_file:
            eval_dir = os.path.dirname(eval_set_path)
            for cf in ["eval_config.json", "test_config.json"]:
                p = os.path.join(eval_dir, cf)
                if os.path.exists(p):
                    config_file = p
                    break

        # 3. なければ、test-executor用のデフォルト設定 (response_match_scoreのみで判定し、軌跡評価を除外する) を使用
        if not config_file:
            # assets/default_eval_config.json のパスを SkillDirectory を使って取得
            default_config_path = self._skill_directory.get_asset_path("default_eval_config.json")
            
            # ファイルが存在しない場合のみ生成
            if not os.path.exists(default_config_path):
                default_config_content = {"criteria": {"response_match_score": 0.8}}
                os.makedirs(os.path.dirname(default_config_path), exist_ok=True)
                with open(default_config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config_content, f, indent=2)
            config_file = default_config_path
        
        return config_file