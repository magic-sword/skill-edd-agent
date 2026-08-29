import pytest
from pathlib import Path
from edd_agent_tools.skills import (
    SkillSpec,
    SkillLogicDraft,
    SkillPattern,
    SkillTemplateEngine,
    SkillValidator,
    SkillsState,
    Skill
)


def test_skills_spec_with_dependencies(tmp_path: Path):
    """SKILL.md に dependencies が宣言されている場合のパースとプロパティアクセスを検証"""
    skill_md = tmp_path / "SKILL.md"
    content = """---
name: composite-workflow
description: "A workflow skill that orchestrates data processing and reporting."
license: Complete terms in LICENSE.txt
pattern: workflow
dependencies:
  - data-cleaner
  - report-generator
---

# Composite Workflow

## Overview
Orchestrates data pipeline.

## Workflow Decision Tree
- **If** data is raw ➔ **Then** clean and report

## Step-by-Step Instructions
### Step 1: Run cleaner
Execute `scripts/run.py`.

## Usage Scenarios & Trigger Examples
- "Run composite workflow."
- "Process raw data."
"""
    skill_md.write_text(content, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run.py").write_text("print('running')", encoding="utf-8")

    spec = SkillSpec.load_from_file(skill_md)
    assert spec.name == "composite-workflow"
    assert spec.dependencies == ["data-cleaner", "report-generator"]

    val_res = SkillValidator.validate_directory(tmp_path)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


def test_dependency_graph_and_cascade_lookup(tmp_path: Path):
    """SkillsState における依存グラフ検証、トポロジカルソート、依存逆引き（get_dependents）を検証"""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # 1. 基礎スキル A (依存なし)
    skill_a = skills_root / "skill-a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("""---
name: skill-a
description: "Atomic skill A."
pattern: task_based
---

# Skill A

## Overview
Atomic skill A.

## Quick Start & Tasks
### Task: do_a
Run `scripts/a.py`.

## Usage Scenarios & Trigger Examples
- "Do task A."
- "Run A."
""", encoding="utf-8")
    (skill_a / "scripts").mkdir()
    (skill_a / "scripts" / "a.py").write_text("# do a", encoding="utf-8")

    # 2. 基礎スキル B (依存なし)
    skill_b = skills_root / "skill-b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text("""---
name: skill-b
description: "Atomic skill B."
pattern: task_based
---

# Skill B

## Overview
Atomic skill B.

## Quick Start & Tasks
### Task: do_b
Run `scripts/b.py`.

## Usage Scenarios & Trigger Examples
- "Do task B."
- "Run B."
""", encoding="utf-8")
    (skill_b / "scripts").mkdir()
    (skill_b / "scripts" / "b.py").write_text("# do b", encoding="utf-8")

    # 3. 上位ワークフロー W (skill-a, skill-b に依存)
    wf_w = skills_root / "workflow-w"
    wf_w.mkdir()
    (wf_w / "SKILL.md").write_text("""---
name: workflow-w
description: "Composite workflow W."
pattern: workflow
dependencies:
  - skill-a
  - skill-b
---

# Workflow W

## Overview
Composite workflow.

## Workflow Decision Tree
- **If** start ➔ **Then** run workflow

## Step-by-Step Instructions
### Step 1: Run
Run `scripts/w.py`.

## Usage Scenarios & Trigger Examples
- "Run workflow W."
- "Execute W."
""", encoding="utf-8")
    (wf_w / "scripts").mkdir()
    (wf_w / "scripts" / "w.py").write_text("# do w", encoding="utf-8")

    # 4. 最上位ワークフロー Top (workflow-w に依存)
    wf_top = skills_root / "workflow-top"
    wf_top.mkdir()
    (wf_top / "SKILL.md").write_text("""---
name: workflow-top
description: "Top-level workflow."
pattern: workflow
dependencies:
  - workflow-w
---

# Workflow Top

## Overview
Top workflow.

## Workflow Decision Tree
- **If** start ➔ **Then** run top

## Step-by-Step Instructions
### Step 1: Run
Run `scripts/top.py`.

## Usage Scenarios & Trigger Examples
- "Run top workflow."
- "Execute top."
""", encoding="utf-8")
    (wf_top / "scripts").mkdir()
    (wf_top / "scripts" / "top.py").write_text("# do top", encoding="utf-8")

    # SkillsState の初期化と検証
    state_file = tmp_path / "skills_state.json"
    state_file.write_text(f"""{{
      "entries": [{{"path": "{skills_root.as_posix()}", "name": "tool"}}],
      "inherits": [],
      "exclude": [],
      "skills": {{}},
      "agents": {{}}
    }}""", encoding="utf-8")

    state = SkillsState(state_path=state_file, project_root=tmp_path)
    
    # 依存関係の正常性確認
    is_valid, errors = state.validate_dependency_graph()
    assert is_valid, f"Expected valid dependency graph, got errors: {errors}"

    # 依存関係の取得
    assert state.get_dependencies("workflow-w") == ["skill-a", "skill-b"]
    assert state.get_dependencies("skill-a") == []

    # 依存逆引き (get_dependents)
    # skill-a に依存している上位スキル ➔ workflow-w
    assert state.get_dependents("skill-a") == ["workflow-w"]
    # workflow-w に依存している上位スキル ➔ workflow-top
    assert state.get_dependents("workflow-w") == ["workflow-top"]

    # 実行順序（トポロジカルソート）
    order = state.get_execution_order()
    assert len(order) == 4
    # skill-a と skill-b は workflow-w より前に来ること
    assert order.index("skill-a") < order.index("workflow-w")
    assert order.index("skill-b") < order.index("workflow-w")
    # workflow-w は workflow-top より前に来ること
    assert order.index("workflow-w") < order.index("workflow-top")


def test_circular_dependency_detection(tmp_path: Path):
    """循環参照（Circular Dependency）が正しく検知されるかを検証"""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # skill-x ➔ skill-y に依存
    skill_x = skills_root / "skill-x"
    skill_x.mkdir()
    (skill_x / "SKILL.md").write_text("""---
name: skill-x
description: "Skill X."
dependencies:
  - skill-y
---
# Skill X
## Overview
X
## Step-by-Step Instructions
### Step 1: Run
Run `scripts/x.py`.
## Usage Scenarios & Trigger Examples
- "X1"
- "X2"
""", encoding="utf-8")
    (skill_x / "scripts").mkdir()
    (skill_x / "scripts" / "x.py").write_text("", encoding="utf-8")

    # skill-y ➔ skill-x に依存（循環！）
    skill_y = skills_root / "skill-y"
    skill_y.mkdir()
    (skill_y / "SKILL.md").write_text("""---
name: skill-y
description: "Skill Y."
dependencies:
  - skill-x
---
# Skill Y
## Overview
Y
## Step-by-Step Instructions
### Step 1: Run
Run `scripts/y.py`.
## Usage Scenarios & Trigger Examples
- "Y1"
- "Y2"
""", encoding="utf-8")
    (skill_y / "scripts").mkdir()
    (skill_y / "scripts" / "y.py").write_text("", encoding="utf-8")

    state_file = tmp_path / "skills_state.json"
    state_file.write_text(f"""{{
      "entries": [{{"path": "{skills_root.as_posix()}", "name": "tool"}}],
      "inherits": [],
      "exclude": [],
      "skills": {{}},
      "agents": {{}}
    }}""", encoding="utf-8")

    state = SkillsState(state_path=state_file, project_root=tmp_path)
    is_valid, errors = state.validate_dependency_graph()
    assert not is_valid
    assert any("循環参照" in e for e in errors)
