"""
A2A互換エージェントサーバーの起動スクリプト。
"""
import os
import sys
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# 起動スクリプトの親ディレクトリを sys.path に追加して、
# カレントディレクトリの設定に影響されずに agent モジュールをインポートできるようにします。
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agent import root_agent

# エージェントを A2A 互換の Starlette アプリケーションに変換します。
# agent_card 引数を省略することにより、大本のエージェントにマウントされた
# すべてのスキル・ワークフロー（ツール）を含む Agent Card が動的に自動生成されます。
a2a_app = to_a2a(
    root_agent,
    port=8001
)

if __name__ == "__main__":
    # Uvicorn サーバーを使用して Web サーバーを起動します。
    # 外部ホストからもアクセスできるように host="0.0.0.0" に設定します。
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)

