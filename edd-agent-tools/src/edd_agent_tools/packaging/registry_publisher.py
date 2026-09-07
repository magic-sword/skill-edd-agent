"""
Agent Registry Publisher for A2A v1.0.0 and Google Enterprise Agent Platforms.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.error
import urllib.request


@dataclass
class PublishReceipt:
    """エージェント公開結果の受領証明データモデル。"""
    agent_id: str
    agent_name: str
    version: str
    registry_url: str
    published_at: str
    checksum_sha256: str
    skills_count: int
    status: str
    response_metadata: Dict[str, Any]


class AgentRegistryPublisher:
    """Agent Card を Agent Registry (A2A v1.0.0) へ公開・登録するパブリッシャー。"""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()

    def validate_card_payload(self, card_data: Dict[str, Any]) -> None:
        """A2A v1.0.0 仕様に従ってカードの必須項目を検証する。"""
        required_fields = ["name", "description", "version", "supportedInterfaces", "skills"]
        for field in required_fields:
            if field not in card_data:
                raise ValueError(f"Agent Card に必須フィールド '{field}' が存在しません。")

        if not isinstance(card_data["supportedInterfaces"], list) or not card_data["supportedInterfaces"]:
            raise ValueError("Agent Card の 'supportedInterfaces' は空でない配列である必要があります。")

        for iface in card_data["supportedInterfaces"]:
            if "protocolVersion" not in iface or iface["protocolVersion"] != "1.0.0":
                raise ValueError("supportedInterfaces の protocolVersion は '1.0.0' である必要があります。")

    def publish(
        self,
        card_path: Path,
        registry_url: str = "http://localhost:8080/v1/agents",
        dry_run: bool = False,
        api_token: Optional[str] = None,
        output_receipt_path: Optional[Path] = None,
    ) -> PublishReceipt:
        """Agent Card をレジストリへ送信・公開し、発行受領書 (Receipt) を生成する。"""
        if not card_path.is_absolute():
            card_path = self.workspace_root / card_path

        if not card_path.exists():
            raise FileNotFoundError(f"Agent Card が見つかりません: {card_path}")

        with open(card_path, "r", encoding="utf-8") as f:
            card_data = json.load(f)

        self.validate_card_payload(card_data)

        raw_bytes = json.dumps(card_data, sort_keys=True, indent=2).encode("utf-8")
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()
        agent_id = card_data.get("id", f"agent-{card_data['name'].lower().replace(' ', '-')}")
        skills_count = len(card_data.get("skills", []))

        if dry_run:
            receipt = PublishReceipt(
                agent_id=agent_id,
                agent_name=card_data["name"],
                version=card_data.get("version", "1.0.0"),
                registry_url=registry_url,
                published_at=now_iso,
                checksum_sha256=checksum,
                skills_count=skills_count,
                status="DRY_RUN_VALIDATED",
                response_metadata={"dry_run": True, "message": "Payload is structurally valid for A2A v1.0.0 registry."},
            )
        else:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "edd-agent-tools/1.0.0 (AgentRegistryPublisher)",
            }
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"

            req = urllib.request.Request(
                registry_url,
                data=raw_bytes,
                headers=headers,
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_body = resp.read().decode("utf-8")
                    meta = json.loads(resp_body) if resp_body else {}
                    status = "SUCCESS"
            except urllib.error.URLError as e:
                status = f"FAILED: {e.reason}"
                meta = {"error": str(e)}
                raise RuntimeError(f"Agent Registry への接続に失敗しました: {e}") from e

            receipt = PublishReceipt(
                agent_id=agent_id,
                agent_name=card_data["name"],
                version=card_data.get("version", "1.0.0"),
                registry_url=registry_url,
                published_at=now_iso,
                checksum_sha256=checksum,
                skills_count=skills_count,
                status=status,
                response_metadata=meta,
            )

        if output_receipt_path:
            if not output_receipt_path.is_absolute():
                output_receipt_path = self.workspace_root / output_receipt_path
            output_receipt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_receipt_path, "w", encoding="utf-8") as f:
                json.dump(asdict(receipt), f, indent=2, ensure_ascii=False)

        return receipt
