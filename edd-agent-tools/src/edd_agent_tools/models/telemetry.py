"""
Telemetry and Root-Cause Diagnostic Models for Interactive/Game Environments.

Google ADK 2.0 & EDD 評価駆動開発に準拠した、ステップ単位のメトリクス収集および
障害原因分類データモデル。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class StepTelemetry(BaseModel):
    """単一ステップの計測データ."""

    step_index: int = Field(..., description="0-indexed step number")
    action_id: int = Field(..., description="Executed action ID")
    action_name: str = Field(..., description="Executed action name (e.g., ACTION1, CLICK)")
    action_data: Dict[str, Any] = Field(default_factory=dict, description="Action parameters (e.g. coordinates)")
    reasoning: Optional[Any] = Field(default=None, description="Agent reasoning or internal thought trace")
    state_before: str = Field(..., description="State or hash before action")
    state_after: str = Field(..., description="State or hash after action")
    levels_completed: int = Field(default=0, description="Cumulative levels completed")
    win_levels: int = Field(default=0, description="Total levels required for win")
    pixels_changed: int = Field(default=0, description="Number of pixels or state tokens changed")
    changed_colors: List[int] = Field(default_factory=list, description="IDs of colors or tokens that changed")
    is_effective: bool = Field(..., description="Whether action produced an effective change in environment")
    time_taken_ms: float = Field(default=0.0, description="Execution time in milliseconds")


class SessionTelemetry(BaseModel):
    """1ゲーム/1セッション全体の計測データ."""

    game_id: str = Field(..., description="Unique environment or game identifier")
    title: str = Field(default="", description="Short environment title or label")
    baseline_actions: List[int] = Field(default_factory=list, description="Allowed action IDs")
    steps: List[StepTelemetry] = Field(default_factory=list, description="List of step records")
    initial_shape: Tuple[int, int] = Field(default=(0, 0), description="Initial observation dimensions")
    final_state: str = Field(default="NOT_FINISHED", description="Final game state (e.g. GAME_OVER, WIN)")
    total_levels_completed: int = Field(default=0, description="Total levels completed")
    total_win_levels: int = Field(default=0, description="Total win levels")
    total_time_sec: float = Field(default=0.0, description="Total elapsed time in seconds")

    def add_step(self, step: StepTelemetry) -> None:
        self.steps.append(step)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def effective_steps(self) -> int:
        return sum(1 for s in self.steps if s.is_effective)

    @property
    def effective_ratio(self) -> float:
        if not self.steps:
            return 0.0
        return self.effective_steps / len(self.steps)


class DiagnosticReport(BaseModel):
    """セッションの根本原因診断レポート."""

    game_id: str
    title: str
    total_steps: int
    levels_completed: int
    win_levels: int
    effective_ratio: float
    max_consecutive_stagnation: int
    dominant_failure_category: str
    primary_recommendation: str
    action_stats: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    click_stats: Dict[str, Any] = Field(default_factory=dict)
