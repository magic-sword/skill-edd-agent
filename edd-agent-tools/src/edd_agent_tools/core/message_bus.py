"""
File-based Message Bus for Inter-Skill Communication (Whitepaper Section 7 Pipeline Pattern).
Decouples large data payloads from the LLM Context Window using local URIs and schema validation.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class BusMessage:
    """メッセージバス上で受け渡されるメッセージデータ構造。"""
    message_id: str
    channel: str
    schema_name: str
    created_at: str
    payload: Any
    checksum_sha256: str
    file_uri: str
    metadata: Dict[str, Any]


class FileMessageBus:
    """ファイルベースのスキル間メッセージバス（Pipeline Pattern 実装基盤）。"""

    def __init__(self, bus_dir: Optional[Path] = None, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.bus_dir = bus_dir or (self.workspace_root / ".agents" / "bus")
        self.bus_dir.mkdir(parents=True, exist_ok=True)

    def publish_message(
        self,
        channel: str,
        payload: Any,
        schema_name: str = "generic_json",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BusMessage:
        """メッセージをファイルとして永続化し、URI を含む BusMessage を返す。"""
        msg_id = f"msg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        channel_dir = self.bus_dir / channel
        channel_dir.mkdir(parents=True, exist_ok=True)

        payload_bytes = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()

        target_file = channel_dir / f"{msg_id}.json"
        now_iso = datetime.now(timezone.utc).isoformat()
        file_uri = target_file.as_uri()

        msg = BusMessage(
            message_id=msg_id,
            channel=channel,
            schema_name=schema_name,
            created_at=now_iso,
            payload=payload,
            checksum_sha256=checksum,
            file_uri=file_uri,
            metadata=metadata or {},
        )

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(asdict(msg), f, indent=2, ensure_ascii=False)

        return msg

    def read_message(self, message_uri_or_path: str) -> BusMessage:
        """URI またはファイルパスからメッセージを読み取り、完全性（SHA-256）を検証する。"""
        if message_uri_or_path.startswith("file://"):
            path_str = message_uri_or_path[7:]
            p = Path(path_str)
        else:
            p = Path(message_uri_or_path)
            if not p.is_absolute():
                p = self.workspace_root / p

        if not p.exists():
            raise FileNotFoundError(f"Bus message not found: {p}")

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        payload_bytes = json.dumps(data["payload"], sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")
        calculated_checksum = hashlib.sha256(payload_bytes).hexdigest()

        if calculated_checksum != data.get("checksum_sha256"):
            raise ValueError(f"Message checksum mismatch! Potential data corruption: {p}")

        return BusMessage(
            message_id=data["message_id"],
            channel=data["channel"],
            schema_name=data.get("schema_name", "generic_json"),
            created_at=data["created_at"],
            payload=data["payload"],
            checksum_sha256=data["checksum_sha256"],
            file_uri=data["file_uri"],
            metadata=data.get("metadata", {}),
        )

    def list_messages(self, channel: Optional[str] = None) -> List[BusMessage]:
        """指定チャネル内のメッセージ一覧を最新順に取得する。"""
        search_dir = (self.bus_dir / channel) if channel else self.bus_dir
        if not search_dir.exists():
            return []

        json_files = sorted(search_dir.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        messages = []
        for jf in json_files:
            try:
                messages.append(self.read_message(str(jf)))
            except Exception:
                continue
        return messages

    def clear_channel(self, channel: str) -> int:
        """指定したチャネル内のメッセージをすべて削除する。"""
        channel_dir = self.bus_dir / channel
        if not channel_dir.exists():
            return 0

        count = 0
        for f in channel_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        return count
