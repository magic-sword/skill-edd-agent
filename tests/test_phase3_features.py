"""
Tests for Phase 3 Features:
1. AgentRegistryPublisher (edd publish / A2A v1.0.0 registration)
2. FileMessageBus (Pipeline pattern message bus & data integrity)
3. library-evolver meta-skill and LibraryEvolverPipeline
4. CLI Phase 3 command dispatch
"""

import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from edd_agent_tools.packaging.registry_publisher import AgentRegistryPublisher, PublishReceipt
from edd_agent_tools.core.message_bus import FileMessageBus, BusMessage
from edd_agent_tools.cli import main
from edd_agent_tools.state import SkillsState


def test_agent_registry_publisher_dry_run(tmp_path: Path):
    """AgentRegistryPublisher が dry_run モードで Agent Card を正しく検証し受領書を生成することを検証"""
    card_path = tmp_path / "agent-card.json"
    card_data = {
        "name": "test_agent",
        "description": "Test Agent for Unit Test",
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": "http://localhost:8001",
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0.0"
            }
        ],
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "skill_1",
                "name": "case-converter",
                "description": "Convert string cases",
                "tags": ["text"]
            }
        ]
    }
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(card_data, f)

    publisher = AgentRegistryPublisher(workspace_root=tmp_path)
    receipt_path = tmp_path / "receipt.json"

    receipt = publisher.publish(
        card_path=card_path,
        registry_url="http://mock-registry.example.com/v1/agents",
        dry_run=True,
        output_receipt_path=receipt_path
    )

    assert isinstance(receipt, PublishReceipt)
    assert receipt.status == "DRY_RUN_VALIDATED"
    assert receipt.agent_name == "test_agent"
    assert receipt.skills_count == 1
    assert len(receipt.checksum_sha256) == 64
    assert receipt_path.exists()


def test_agent_registry_publisher_validation_failure(tmp_path: Path):
    """無効な Agent Card（supportedInterfaces 欠損）を検出して拒絶することを検証"""
    invalid_card = tmp_path / "invalid-card.json"
    with open(invalid_card, "w", encoding="utf-8") as f:
        json.dump({"name": "bad_agent", "version": "1.0.0"}, f)

    publisher = AgentRegistryPublisher(workspace_root=tmp_path)
    with pytest.raises(ValueError, match="必須フィールド"):
        publisher.publish(card_path=invalid_card, dry_run=True)


def test_file_message_bus_workflow(tmp_path: Path):
    """FileMessageBus によるメッセージの発行・読み取り・完全性検証をテスト"""
    bus = FileMessageBus(bus_dir=tmp_path / "bus", workspace_root=tmp_path)

    # 1. Publish
    payload = {"data": [1, 2, 3], "status": "computed"}
    msg = bus.publish_message(
        channel="analytics",
        payload=payload,
        schema_name="analysis_result",
        metadata={"source": "pytest"}
    )

    assert isinstance(msg, BusMessage)
    assert msg.channel == "analytics"
    assert msg.payload == payload
    assert Path(msg.file_uri.replace("file://", "")).exists()

    # 2. Read
    read_msg = bus.read_message(msg.file_uri)
    assert read_msg.message_id == msg.message_id
    assert read_msg.payload == payload
    assert read_msg.checksum_sha256 == msg.checksum_sha256

    # 3. List
    messages = bus.list_messages("analytics")
    assert len(messages) == 1
    assert messages[0].message_id == msg.message_id

    # 4. Clear
    cleared = bus.clear_channel("analytics")
    assert cleared == 1
    assert len(bus.list_messages("analytics")) == 0


def test_file_message_bus_tamper_detection(tmp_path: Path):
    """ペイロードが改ざんされた場合に Checksum mismatch を検知することを検証"""
    bus = FileMessageBus(bus_dir=tmp_path / "bus", workspace_root=tmp_path)
    msg = bus.publish_message(channel="secure", payload={"secret": "abc"})

    file_path = Path(msg.file_uri.replace("file://", ""))
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 改ざん
    data["payload"]["secret"] = "tampered"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Message checksum mismatch"):
        bus.read_message(msg.file_uri)


def test_library_evolver_script_plan_and_execution():
    """library_evolver スクリプトの計画フェーズの動作をテスト"""
    import importlib.util

    script_path = Path("/workspace/src/skills/library-evolver/scripts/library_evolver.py")
    spec = importlib.util.spec_from_file_location("library_evolver", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    pipeline = module.LibraryEvolverPipeline()
    plan_res = pipeline.plan_skill_evolution(
        target_task_desc="Analyze sentiment in text",
        suggested_skill_name="sentiment-analyzer",
        pattern="task_based"
    )

    assert plan_res["status"] == "planned"
    assert plan_res["suggested_skill_name"] == "sentiment-analyzer"
    assert plan_res["decision"] in ["SYNTHESIZE_NEW", "EVOLVE_EXISTING", "MERGE_OR_REFINE"]


def test_cli_phase3_publish_dispatch(tmp_path: Path):
    """CLI edd publish --dry-run が正常にディスパッチされることを検証"""
    card_path = tmp_path / "agent-card.json"
    card_data = {
        "name": "cli_agent",
        "description": "CLI Test Agent",
        "version": "1.0.0",
        "supportedInterfaces": [{"url": "http://localhost:8001", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0.0"}],
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": []
    }
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(card_data, f)

    exit_code = main(["publish", "--card-path", str(card_path), "--dry-run"])
    assert exit_code == 0
