"""
Unified State and Discovery Management for edd-agent-tools

skills_state.json および skills.json の管理とスキル探索・依存関係 DAG 解析。
他プロジェクトへ配布された環境でも自動パス解決が可能な Zero-Hardcoding 設計。
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set

from .models.state import SkillsStateJson, SkillEntry, InheritEntry, SkillTier, ProjectSkillInfo
from .skill import Skill


class SkillsState:
    """skills_state.json のロード、保存、および ADK仕様に準拠したスキル探索を行う状態管理クラス。"""

    def __init__(
        self,
        state_path: Optional[Path | str] = None,
        project_root: Optional[Path | str] = None,
        skills_roots: Optional[List[Path | str]] = None
    ):
        # 1. プロジェクトルートの決定
        if project_root:
            self.project_root = Path(project_root).resolve()
        elif "EDD_PROJECT_ROOT" in os.environ:
            self.project_root = Path(os.environ["EDD_PROJECT_ROOT"]).resolve()
        else:
            self.project_root = Path(os.getcwd()).resolve()

        # 2. 状態ファイルパスの決定
        if state_path:
            self.state_path = Path(state_path).resolve()
        else:
            self.state_path = self.project_root / "skills_state.json"

        # skills.json は常に skills_state.json と同一ディレクトリに出力
        self.skills_json_path = self.state_path.parent / "skills.json"

        # 3. 追加探索パス
        self.custom_skills_roots = [Path(p).resolve() for p in (skills_roots or [])]
        if "EDD_SKILLS_PATH" in os.environ:
            for p in os.environ["EDD_SKILLS_PATH"].split(os.pathsep):
                if p.strip():
                    self.custom_skills_roots.append(Path(p.strip()).resolve())

        self.data: Optional[SkillsStateJson] = None
        self._cached_skills: Optional[Dict[str, Skill]] = None

    def _get_default_search_entries(self) -> List[SkillEntry]:
        """プロジェクト内の標準スキルディレクトリ候補を探索エントリとして生成"""
        candidates = [
            Path("src/skills"),
            Path("skills"),
            Path(".agents/skills"),
            Path(".")
        ]
        entries = []
        for cand in candidates:
            entries.append(SkillEntry(path=cand))
        return entries

    def load(self) -> SkillsStateJson:
        """skills_state.json をロードし、メモリ上に保持します。存在しない場合はデフォルト構成で初期化します。"""
        self._cached_skills = None
        if not self.state_path.exists():
            self.data = SkillsStateJson(
                entries=self._get_default_search_entries(),
                inherits=[],
                exclude=[]
            )
            return self.data

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.data = SkillsStateJson.model_validate_json(f.read())
        except Exception as e:
            raise RuntimeError(f"エラー: {self.state_path} の読み込みまたはバリデーションに失敗しました: {e}")
        return self.data

    def export_to_skills_json(self, filter_tier: Optional[SkillTier] = None) -> dict:
        """skills_state.json から 'skills' 属性を除外し、Tier による exclude フィルタリングを施した ADK公式の skills.json 用データを生成します。"""
        if self.data is None:
            self.load()

        threshold = SkillTier.READ_ONLY if filter_tier is None else filter_tier
        data_dict = json.loads(self.data.model_dump_json())

        if "skills" in data_dict:
            del data_dict["skills"]
        if "agents" in data_dict:
            del data_dict["agents"]

        if "entries" in data_dict:
            for entry in data_dict["entries"]:
                if "path" in entry:
                    entry["path"] = entry["path"].replace("\\", "/")

        if "inherits" in data_dict:
            for inherit in data_dict["inherits"]:
                if "path" in inherit:
                    inherit["path"] = inherit["path"].replace("\\", "/")

        discovered = self.scan_skills()
        exclude_set = set(data_dict.get("exclude", []))

        for logical_name, skill_obj in discovered.items():
            if skill_obj._tier < threshold:
                exclude_set.add(logical_name)

        data_dict["exclude"] = sorted(list(exclude_set))
        return data_dict

    def save(self, filter_tier: Optional[SkillTier] = None):
        """現在のメモリ状態を skills_state.json ファイルへ書き出し、かつ適正な構成で skills.json へマウントします。"""
        if self.data is None:
            raise RuntimeError("エラー: データがロードされていません。")

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                f.write(self.data.model_dump_json(indent=2))
        except Exception as e:
            raise RuntimeError(f"エラー: {self.state_path} の保存に失敗しました: {e}")

        # skills.json も同時に更新
        skills_json_data = self.export_to_skills_json(filter_tier=filter_tier)
        try:
            with open(self.skills_json_path, "w", encoding="utf-8") as f:
                json.dump(skills_json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"エラー: {self.skills_json_path} の保存に失敗しました: {e}")

    def scan_skills(self) -> Dict[str, Skill]:
        """設定された全エントリおよびカスタムパスからスキルを再帰的にスキャンして検出します。"""
        if self._cached_skills is not None:
            return self._cached_skills

        if self.data is None:
            self.load()

        discovered: Dict[str, Skill] = {}

        # 1. inherits の処理
        for inherit in self.data.inherits:
            inherit_file = (self.project_root / inherit.path).resolve()
            if inherit_file.exists():
                try:
                    sub_state = SkillsState(state_path=inherit_file, project_root=self.project_root)
                    sub_skills = sub_state.scan_skills()
                    discovered.update(sub_skills)
                except Exception:
                    pass

        # 2. entries の処理
        for entry in self.data.entries:
            target_path = (self.project_root / entry.path).resolve()
            if not target_path.exists():
                continue

            if (target_path / "SKILL.md").exists():
                skill_name = entry.name or target_path.name
                if skill_name not in self.data.exclude:
                    tier_val = self._get_tier_for_skill(skill_name)
                    discovered[skill_name] = Skill(target_path, tier=tier_val)
            elif target_path.is_dir():
                for sub_dir in sorted(target_path.iterdir()):
                    if sub_dir.is_dir() and (sub_dir / "SKILL.md").exists():
                        skill_name = sub_dir.name
                        if skill_name not in self.data.exclude:
                            tier_val = self._get_tier_for_skill(skill_name)
                            discovered[skill_name] = Skill(sub_dir, tier=tier_val)

        # 3. カスタム探索パス
        for cp in self.custom_skills_roots:
            if not cp.exists() or not cp.is_dir():
                continue
            if (cp / "SKILL.md").exists():
                skill_name = cp.name
                if skill_name not in self.data.exclude:
                    tier_val = self._get_tier_for_skill(skill_name)
                    discovered[skill_name] = Skill(cp, tier=tier_val)
            else:
                for child in sorted(cp.iterdir()):
                    if child.is_dir() and (child / "SKILL.md").exists():
                        skill_name = child.name
                        if skill_name not in self.data.exclude:
                            tier_val = self._get_tier_for_skill(skill_name)
                            discovered[skill_name] = Skill(child, tier=tier_val)

        self._cached_skills = discovered
        return discovered

    def _get_tier_for_skill(self, skill_name: str) -> int:
        """skills_state.json から指定スキルの Tier を取得"""
        if self.data and self.data.skills and skill_name in self.data.skills:
            t = self.data.skills[skill_name].tier
            return t.value if hasattr(t, "value") else int(t)
        return int(SkillTier.SANDBOX)

    def get_skill(self, name: str) -> Optional[Skill]:
        """論理名からスキルを取得します。"""
        skills = self.scan_skills()
        if name in skills:
            return skills[name]

        # 直接探索フォールバック
        for cand_dir in [self.project_root / "src" / "skills" / name, self.project_root / "skills" / name]:
            if cand_dir.exists() and (cand_dir / "SKILL.md").exists():
                return Skill(root_dir=cand_dir, tier=self._get_tier_for_skill(name))

        return None

    def list_skills(self) -> List[Skill]:
        """検出された全スキルオブジェクトのリストを返します。"""
        return list(self.scan_skills().values())

    def register_skill(self, skill_name: str, tier: SkillTier | int = SkillTier.SANDBOX):
        """指定されたスキルの Tier を更新・登録し、永続化します。"""
        self.set_skill_tier(skill_name, tier)

    def set_skill_tier(self, skill_name: str, tier: SkillTier | int):
        """指定されたスキルの Tier を更新し、永続化します。"""
        if self.data is None:
            self.load()

        tier_enum = SkillTier(tier) if isinstance(tier, int) else tier
        if self.data.skills is None:
            self.data.skills = {}

        self.data.skills[skill_name] = ProjectSkillInfo(tier=tier_enum)
        self._cached_skills = None
        self.save()

    def update_skill_tier(self, skill_name: str, tier: SkillTier | int):
        """set_skill_tier のエイリアス"""
        self.set_skill_tier(skill_name, tier)

    # ==========================================
    # DAG 依存関係解析 & 循環参照検出
    # ==========================================

    def get_dependencies(self, skill_name: str) -> List[str]:
        """指定されたスキルの依存先スキル名一覧を取得します。"""
        skill = self.get_skill(skill_name)
        return skill.dependencies if skill else []

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """全スキルの依存関係 DAG を構築します。"""
        skills = self.scan_skills()
        graph: Dict[str, List[str]] = {}
        for name, skill in skills.items():
            graph[name] = skill.dependencies
        return graph

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """build_dependency_graph のエイリアス"""
        return self.build_dependency_graph()

    def validate_dependency_graph(self) -> Tuple[bool, List[str]]:
        """依存関係グラフの整合性（存在しない依存先、循環依存）を検証します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()
        errors: List[str] = []

        # 1. 存在確認
        for name, deps in graph.items():
            for dep in deps:
                if dep not in skills:
                    errors.append(f"Skill '{name}' depends on non-existent skill '{dep}'.")

        # 2. 循環依存検知 (DFS)
        visited = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str, path: List[str]) -> bool:
            visited[node] = 1
            for neighbor in graph.get(node, []):
                if neighbor not in skills:
                    continue
                if visited.get(neighbor, 0) == 1:
                    cycle_path = " -> ".join(path + [neighbor])
                    errors.append(f"循環参照 (Circular dependency) を検知しました: {cycle_path}")
                    return False
                if visited.get(neighbor, 0) == 0:
                    if not dfs(neighbor, path + [neighbor]):
                        return False
            visited[node] = 2
            return True

        for s in skills:
            if visited.get(s, 0) == 0:
                dfs(s, [s])

        return len(errors) == 0, errors

    def get_dependents(self, skill_name: str) -> List[str]:
        """指定したスキルを直接依存している上位スキル名リスト（逆引き）を返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()
        dependents = []
        for parent, deps in graph.items():
            if skill_name in deps:
                dependents.append(parent)
        return sorted(dependents)

    def get_cascade_dependents(self, skill_name: str) -> List[str]:
        """指定したスキルが更新された際に、再テストが必要な依存先（逆依存先）リストをトポロジカル順で返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()

        reverse_graph: Dict[str, List[str]] = {s: [] for s in skills}
        for parent, deps in graph.items():
            for d in deps:
                if d in reverse_graph:
                    reverse_graph[d].append(parent)

        dependents: List[str] = []
        queue = [skill_name]
        seen = {skill_name}

        while queue:
            curr = queue.pop(0)
            for child in reverse_graph.get(curr, []):
                if child not in seen:
                    seen.add(child)
                    dependents.append(child)
                    queue.append(child)

        return dependents

    def get_cascade_affected_skills(self, skill_name: str) -> List[str]:
        """get_cascade_dependents のエイリアス"""
        return self.get_cascade_dependents(skill_name)

    def get_execution_order(self) -> List[str]:
        """依存関係 DAG に基づき、依存される側が先頭に来るトポロジカル実行順序リストを返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()

        in_degree = {s: 0 for s in skills}
        adj = {s: [] for s in skills}
        for u, deps in graph.items():
            for v in deps:
                if v in adj:
                    adj[v].append(u)
                    in_degree[u] += 1

        queue = [s for s, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        for s in skills:
            if s not in order:
                order.append(s)

        return order
