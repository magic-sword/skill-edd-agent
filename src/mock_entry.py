"""
評価（モックシミュレーション）用のエージェント・エントリーポイント。
本番の agent.py をロードし、動的に mock_agent のコールバックを結合してエクスポートします。
"""
import sys
import pathlib

# 親ディレクトリを sys.path に追加してインポート可能にします
current_dir = pathlib.Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 本番エージェントと、モック用のコールバック関数をロード
from agent import root_agent as base_agent
# 本番エージェントと、モック用のコールバック関数をロード
from agent import root_agent as base_agent
from agents.mock_agent import before_tool_callback

# 本番エージェントを一切汚さず、モック用の before_tool_callback をアタッチ
base_agent.before_tool_callback = before_tool_callback
