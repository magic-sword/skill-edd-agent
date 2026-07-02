import pathlib
import os
import sys
import json
from google.adk.skills import load_skill_from_dir

# src ディレクトリのパスを取得します（/workspace/src/agents/common.py の親の親）
src_dir = pathlib.Path(__file__).parent.parent
skills_dir = src_dir / "skills"

# 評価モードの判定
is_eval_mode = os.environ.get("ADK_EVAL_MODE") == "1"

# システムスキル定義
system_skills = {"skill-generator", "skill-manager", "trigger-evaluator", "eval-unit-tester", "test-executor"}

def load_registry():
    registry_path = src_dir / "skills_registry.json"
    if not registry_path.exists():
        return {"skills": {}}
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"skills": {}}

def load_all_skills(exclude_system=False, target_eval_skill=None):
    """
    登録されているスキルをスキャンし、必要に応じてフィルタリングしてロードします。
    """
    registry = load_registry()
    registered_skills = registry.get("skills", {})
    
    loaded_skills = []
    if skills_dir.exists():
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill_name = skill_path.name
                
                is_system = skill_name in system_skills
                
                # システムスキルの除外判定
                if exclude_system and is_system:
                    continue
                
                # 登録情報を取得
                skill_info = registered_skills.get(skill_name)
                
                # 未登録かつ評価対象でもないスキルはスキップ
                if not is_system and not skill_info and skill_name != target_eval_skill:
                    continue
                    
                # tier 0 (試験中) のスキルは、現在評価中のスキル(target_eval_skill) でない限りスキップ
                if skill_info and skill_info.get("tier") == 0 and skill_name != target_eval_skill:
                    continue
                    
                # 評価モード時の追加の除外ロジック
                if is_eval_mode:
                    if is_system:
                        continue # システム開発スキルを排除
                    if target_eval_skill and skill_name != target_eval_skill:
                        continue # 評価対象外の別スキルを排除して混同を防ぐ
                        
                try:
                    skill = load_skill_from_dir(skill_path)
                    loaded_skills.append(skill)
                except Exception as e:
                    print(f"Warning: Failed to load skill from {skill_path}: {e}", file=sys.stderr)
                    
    return loaded_skills
