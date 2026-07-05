"""
評価（モックシミュレーション）用のエージェント・エントリモジュール。
本番の agent.py をロードし、動的に mock_agent のコールバックを結合してエクスポートします。
"""
import importlib.util
import sys
import pathlib

# 親の src ディレクトリを sys.path に追加
current_dir = pathlib.Path(__file__).parent.resolve()
src_dir = current_dir.parent.resolve()
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 本番の agent.py を別名で明示的にファイルからロードしてインポートの衝突を防ぎます
agent_py_path = src_dir / "agent.py"
spec = importlib.util.spec_from_file_location("real_agent", str(agent_py_path))
real_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_agent)

# モック用のコールバック関数をロード
from agents.mock_agent import before_tool_callback

# 本番エージェントにモック用の before_tool_callback をアタッチ
real_agent.root_agent.before_tool_callback = before_tool_callback

# adk eval は agent_module.agent.root_agent を参照するため、
# このモジュールのメンバ変数として 'agent' を定義して real_agent を参照させます
agent = real_agent
