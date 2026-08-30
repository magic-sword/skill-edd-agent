"""
Core Protocols for edd-agent-tools

エージェント環境およびサンドボックス実行の抽象プロトコル定義。
"""

from typing import Protocol, runtime_checkable, Any
from pathlib import Path


@runtime_checkable
class WorkspaceEnvProtocol(Protocol):
    """ワークスペース仮想実行環境のプロトコルインターフェース。"""

    def step(self, action: Any) -> Any:
        """アクションを実行し、環境の観測結果（Observation）を返します。"""
        ...

    def reset(self) -> Any:
        """環境を初期状態にリセットします。"""
        ...
