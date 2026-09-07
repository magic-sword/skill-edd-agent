"""
Canary Deployment Manager (CanaryDeploymentManager)

Google 『Agent Skills』ホワイトペーパー（May 2026）Table 1 Pattern 5 (p.20), Figure 2 (p.21) 準拠：
本番トラフィックの制御された割合（例: 1%〜5%）のみに新スキルを投入し、
エラー率、例外、およびユーザーフォールバックをリアルタイム監視して
安全なフルロールアウト（Promote）または自動中断・ロールバック（Abort）を制御するマネージャー。
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from edd_agent_tools.state import SkillsState


class CanaryMetrics(BaseModel):
    """Canary 実行メトリクスデータ"""
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    latencies: List[float] = Field(default_factory=list)


class CanaryDeployment(BaseModel):
    """Canary デプロイメント状態"""
    skill_name: str
    traffic_ratio: float = 0.05  # 5% トラフィック
    max_error_rate: float = 0.02  # 許容最大エラー率 2%
    status: str = "MONITORING"  # MONITORING, PROMOTED, ABORTED
    start_time: str = ""
    canary_metrics: CanaryMetrics = Field(default_factory=CanaryMetrics)
    baseline_metrics: CanaryMetrics = Field(default_factory=CanaryMetrics)


class CanaryHealthReport(BaseModel):
    """Canary 健全性監査レポート"""
    skill_name: str
    status: str
    traffic_ratio: float
    total_requests: int
    canary_error_rate: float
    baseline_error_rate: float
    health_status: str  # HEALTHY, WARNING, DEGRADED, READY_TO_PROMOTE
    action_recommendation: str  # CONTINUE_MONITORING, PROMOTE, ABORT_AND_ROLLBACK
    details: str = ""


class CanaryDeploymentManager:
    """Canary トラフィック分割およびヘルスチェックを司るマネージャー"""

    def __init__(self, state_file: Optional[Path] = None, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.state_file = state_file or (self.workspace_root / ".agents" / "canary_deployments.json")
        self.deployments: Dict[str, CanaryDeployment] = self._load_deployments()

    def _load_deployments(self) -> Dict[str, CanaryDeployment]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {k: CanaryDeployment(**v) for k, v in data.items()}
            except Exception:
                return {}
        return {}

    def _save_deployments(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({k: v.model_dump() for k, v in self.deployments.items()}, f, indent=2)

    def register_canary(
        self,
        skill_name: str,
        traffic_ratio: float = 0.05,
        max_error_rate: float = 0.02
    ) -> CanaryDeployment:
        """新しい Canary デプロイを登録します。"""
        import datetime
        dep = CanaryDeployment(
            skill_name=skill_name,
            traffic_ratio=traffic_ratio,
            max_error_rate=max_error_rate,
            status="MONITORING",
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        self.deployments[skill_name] = dep
        self._save_deployments()
        return dep

    def should_route_to_canary(self, skill_name: str, session_id: str) -> bool:
        """セッションIDに基づき決定論的に Canary へルーティングするか判定します。"""
        dep = self.deployments.get(skill_name)
        if not dep or dep.status != "MONITORING":
            return False

        # MD5 ハッシュの下位値を 0.0〜1.0 に正規化して決定論的分割
        h = hashlib.md5(f"{skill_name}:{session_id}".encode("utf-8")).hexdigest()
        norm_val = int(h[:8], 16) / 0xFFFFFFFF
        return norm_val < dep.traffic_ratio

    def record_request(
        self,
        skill_name: str,
        session_id: str,
        success: bool,
        latency_ms: float = 0.0,
        is_canary: Optional[bool] = None
    ):
        """リクエスト実行結果をメトリクスに記録します。"""
        dep = self.deployments.get(skill_name)
        if not dep:
            return

        if is_canary is None:
            is_canary = self.should_route_to_canary(skill_name, session_id)

        target_m = dep.canary_metrics if is_canary else dep.baseline_metrics
        target_m.total_requests += 1
        if success:
            target_m.success_requests += 1
        else:
            target_m.failed_requests += 1

        target_m.error_rate = target_m.failed_requests / target_m.total_requests
        target_m.latencies.append(latency_ms)
        target_m.avg_latency_ms = sum(target_m.latencies) / len(target_m.latencies)

        self._save_deployments()

    def evaluate_canary_health(self, skill_name: str) -> CanaryHealthReport:
        """Canary の健全性を評価し、昇格または中断（ロールバック）の推奨を返します。"""
        dep = self.deployments.get(skill_name)
        if not dep:
            raise ValueError(f"No canary deployment found for skill '{skill_name}'")

        canary_m = dep.canary_metrics
        baseline_m = dep.baseline_metrics

        c_err = canary_m.error_rate
        b_err = baseline_m.error_rate

        # 評価基準
        if canary_m.total_requests < 10:
            health = "HEALTHY"
            rec = "CONTINUE_MONITORING"
            details = f"Collecting sample traffic ({canary_m.total_requests}/10 requests)."
        elif c_err > dep.max_error_rate:
            health = "DEGRADED"
            rec = "ABORT_AND_ROLLBACK"
            details = f"Canary error rate ({c_err:.1%}) exceeds threshold ({dep.max_error_rate:.1%})."
        elif canary_m.total_requests >= 50 and c_err <= dep.max_error_rate:
            health = "READY_TO_PROMOTE"
            rec = "PROMOTE"
            details = f"Canary passed stability criteria ({canary_m.total_requests} requests, {c_err:.1%} error rate)."
        else:
            health = "HEALTHY"
            rec = "CONTINUE_MONITORING"
            details = f"Operating normally ({canary_m.total_requests} requests, error rate: {c_err:.1%})."

        return CanaryHealthReport(
            skill_name=skill_name,
            status=dep.status,
            traffic_ratio=dep.traffic_ratio,
            total_requests=canary_m.total_requests,
            canary_error_rate=c_err,
            baseline_error_rate=b_err,
            health_status=health,
            action_recommendation=rec,
            details=details
        )

    def promote_canary(self, skill_name: str) -> bool:
        """Canary デプロイを本番フルロールアウトとして昇格完了にします。"""
        dep = self.deployments.get(skill_name)
        if not dep:
            return False
        dep.status = "PROMOTED"
        dep.traffic_ratio = 1.0
        self._save_deployments()
        return True

    def abort_canary(self, skill_name: str, reason: str = "") -> bool:
        """Canary デプロイを中止（ロールバック対象）にします。"""
        dep = self.deployments.get(skill_name)
        if not dep:
            return False
        dep.status = "ABORTED"
        dep.traffic_ratio = 0.0
        self._save_deployments()
        return True
