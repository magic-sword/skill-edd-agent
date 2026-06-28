"""
A2A互換エージェントサーバーの起動スクリプト。
"""
import os
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from agent import root_agent

# agent-card.json の絶対パスを取得します。
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_card_path = os.path.join(current_dir, "agent-card.json")

# エージェントを A2A 互換の Starlette アプリケーションに変換します。
a2a_app = to_a2a(
    root_agent,
    port=8001,
    agent_card=agent_card_path
)

if __name__ == "__main__":
    # Uvicorn サーバーを使用して Web サーバーを起動します。
    # 外部ホストからもアクセスできるように host="0.0.0.0" に設定します。
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
