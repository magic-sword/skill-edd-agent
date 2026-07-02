"""
A2Aプロトコル互換のエージェント・エントリーポイント。
環境変数（ADK_EVAL_MODE）を識別し、適切なエージェント実体をエクスポートします。
"""
import sys
import pathlib

# agentsモジュールを確実にロードできるように、親ディレクトリを sys.path に追加します
current_dir = pathlib.Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from agents.common import is_eval_mode

if is_eval_mode:
    # 評価モード時は、システム開発ツールを除外したクリーンな一般ユーザー用エージェントをロード
    from agents.user_agent import user_agent as root_agent
else:
    # 通常起動時は、システム開発支援用のワークフロー指示を持ったエージェントをロード
    from agents.system_agent import system_agent as root_agent
