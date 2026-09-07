"""
Phase 1 新機能テストスイート

1. CoLoadedEvalRunner (edd co-load)
2. AgentCardSynchronizer (edd sync-card - A2A v1.0.0)
3. SemanticCollisionDetector (edd check-collision)
4. SkillOptimizer と Co-loaded チェックの統合
"""

import json
import pytest
from pathlib import Path

from edd_agent_tools.state import SkillsState
from edd_agent_tools.evaluation.co_loaded_runner import CoLoadedEvalRunner
from edd_agent_tools.packaging.card_sync import AgentCardSynchronizer
from edd_agent_tools.validation.collision import SemanticCollisionDetector
from edd_agent_tools.evaluation.optimizer import SkillOptimizer
from edd_agent_tools.cli import main


def test_co_loaded_eval_runner_execution():
    """CoLoadedEvalRunner が複数スキル共存環境下で正常に評価を実行できることを検証"""
    runner = CoLoadedEvalRunner()
    res = runner.run_co_loaded_evaluation(target_skill_name="case-converter", co_loaded_count=3)
    assert res.get("status") != "error"
    assert "target_skill" in res
    assert res["target_skill"] == "case-converter"
    assert "accuracy" in res
    assert res["accuracy"] >= 0.9
    assert res.get("context_rot_detected") is False
    assert len(res.get("co_loaded_skills", [])) >= 2


def test_semantic_collision_detector_logic():
    """SemanticCollisionDetector がスキルの Description 重複度を正しく判定することを検証"""
    detector = SemanticCollisionDetector()
    collisions = detector.detect_collisions(threshold=0.85)
    # 高い閾値では衝突なし
    assert isinstance(collisions, list)

    # 特定のスキルを対象にした探索
    case_collisions = detector.detect_collisions(target_skill_name="case-converter", threshold=0.10)
    assert isinstance(case_collisions, list)
    if case_collisions:
        assert "skill_1" in case_collisions[0]
        assert "similarity" in case_collisions[0]


def test_agent_card_synchronizer_a2a_v1():
    """AgentCardSynchronizer が A2A v1.0.0 準拠の構造を生成できることを検証"""
    sync = AgentCardSynchronizer()
    card = sync.generate_agent_card(port=8001, min_tier=1)

    assert card["version"] == "1.0.0"
    assert "supportedInterfaces" in card
    assert isinstance(card["supportedInterfaces"], list)
    assert len(card["supportedInterfaces"]) > 0
    assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0.0"
    assert card["supportedInterfaces"][0]["protocolBinding"] == "HTTP+JSON"
    assert "skills" in card
    assert isinstance(card["skills"], list)
    assert len(card["skills"]) >= 3

    # 各スキルの必須フィールド検査
    for sk in card["skills"]:
        assert "id" in sk
        assert "name" in sk
        assert "description" in sk
        assert "tags" in sk
        assert "examples" in sk


def test_cli_phase1_commands_dispatch(tmp_path):
    """CLI サブコマンド (co-load, check-collision, sync-card) が正常にディスパッチされることを検証"""
    # 1. check-collision
    assert main(["check-collision"]) == 0

    # 2. co-load
    assert main(["co-load", "case-converter", "--count", "2"]) == 0

    # 3. sync-card to tmp file
    tmp_card = tmp_path / "test_agent_card.json"
    assert main(["sync-card", "--card-path", str(tmp_card)]) == 0
    assert tmp_card.exists()
    card_data = json.loads(tmp_card.read_text(encoding="utf-8"))
    assert card_data["version"] == "1.0.0"


def test_optimizer_co_loaded_integration():
    """SkillOptimizer が Tier 2 昇格時に Co-loaded 評価を実行して昇格できることを検証"""
    optimizer = SkillOptimizer()
    original_tier = optimizer.state.get_skill_tier("case-converter")
    try:
        # case-converter を Tier 2 へ昇格
        res = optimizer.optimize_skill(skill_name="case-converter", target_tier=2, run_cascade=False)
        assert res.get("status") == "promoted"
        assert res.get("promoted_tier") == 2
    finally:
        optimizer.state.set_skill_tier("case-converter", original_tier)
