"""
Interactive & Gameplay Telemetry Collector for EDD.

動的環境・インタラクティブエージェントの各ステップにおける行動、状態変化、
グリッド差分をリアルタイムに記録・集計する。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from edd_agent_tools.models.telemetry import StepTelemetry, SessionTelemetry


class TelemetryCollector:
    """ステップごとの行動と観測差分を追跡・記録するセッションコレクター."""

    def __init__(self, game_id: str, title: str = "", baseline_actions: Optional[List[int]] = None):
        self.session = SessionTelemetry(
            game_id=game_id,
            title=title,
            baseline_actions=baseline_actions or [],
        )
        self._start_time = time.time()
        self._step_start_time = time.time()

    def start_step(self) -> None:
        self._step_start_time = time.time()

    def record_step(
        self,
        step_index: int,
        action_id: int,
        action_name: str,
        state_before: str,
        state_after: str,
        action_data: Optional[Dict[str, Any]] = None,
        reasoning: Optional[Any] = None,
        levels_completed: int = 0,
        win_levels: int = 0,
        pixels_changed: int = 0,
        changed_colors: Optional[List[int]] = None,
        is_effective: Optional[bool] = None,
    ) -> StepTelemetry:
        """ステップ情報を記録してセッションに追加する."""
        now = time.time()
        time_taken_ms = (now - self._step_start_time) * 1000.0

        if is_effective is None:
            is_effective = (pixels_changed > 0) or (state_before != state_after)

        step = StepTelemetry(
            step_index=step_index,
            action_id=action_id,
            action_name=action_name,
            action_data=action_data or {},
            reasoning=reasoning,
            state_before=state_before,
            state_after=state_after,
            levels_completed=levels_completed,
            win_levels=win_levels,
            pixels_changed=pixels_changed,
            changed_colors=changed_colors or [],
            is_effective=is_effective,
            time_taken_ms=round(time_taken_ms, 2),
        )
        self.session.add_step(step)
        return step

    def finish_session(
        self,
        final_state: str,
        total_levels_completed: int = 0,
        total_win_levels: int = 0,
    ) -> SessionTelemetry:
        """セッション終了時の総括を記録する."""
        self.session.total_time_sec = round(time.time() - self._start_time, 3)
        self.session.final_state = final_state
        self.session.total_levels_completed = total_levels_completed
        self.session.total_win_levels = total_win_levels
        return self.session
