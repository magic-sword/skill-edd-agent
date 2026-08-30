"""
Core State Management for edd-agent-tools

skills_state.json および skills.json の管理とスキル探索・依存関係 DAG 解析。
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from .models import SkillsStateJson, SkillEntry, InheritEntry, SkillTier, ProjectSkillInfo
from .skill import Skill


class SkillsState:
    """skills_state.json のロード、保存、および ADK仕様に準拠したスキル探索（スキャン）を行う状態管理クラス。"""

    def __init__(self, state_path: Optional[Path] = None, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        
        if state_path is None:
            self.state_path = self.project_root / "skills_state.json"
        else:
            self.state_path = Path(state_path).resolve()
        
        # skills.json は常に skills_state.json と同一のディレクトリに固定出力する
        self.skills_json_path = self.state_path.parent / "skills.json"
            
        self.data: Optional[SkillsStateJson] = None
        self._cached_skills: Optional[dict] = None

    def load(self) -> SkillsStateJson:
        """skills_state.json をロードし、メモリ上に保持します。存在しない場合はデフォルト構成で初期化します。"""
        self._cached_skills = None
        if not self.state_path.exists():
            # デフォルトはカレントディレクトリ (.)、src/skills と src/agents を探索対象として初期化
            self.data = SkillsStateJson(
                entries=[
                    SkillEntry(path=Path(".")),
                    SkillEntry(path=Path("src/skills")),
                    SkillEntry(path=Path("src/agents"))
                ],
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

        skills_json_data = self.export_to_skills_json(filter_tier=filter_tier)
        try:
            with open(self.skills_json_path, "w", encoding="utf-8") as f:
                json.dump(skills_json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"エラー: {self.skills_json_path} の保存に失敗しました: {e}")

    def scan_skills(self) -> dict[str, Skill]:
        """ADK仕様に基づき、entries と inherits に従ってスキルを再帰スキャン・解決します。"""
        if self.data is None:
            self.load()

        found_skills: dict[str, Skill] = {}

        for inherit in self.data.inherits:
            inherit_file = (self.project_root / inherit.path).resolve()
            if inherit_file.exists():
                try:
                    sub_state = SkillsState(state_path=inherit_file, project_root=self.project_root)
                    sub_skills = sub_state.scan_skills()
                    found_skills.update(sub_skills)
                except Exception:
                    pass

        for entry in self.data.entries:
            target_path = (self.project_root / entry.path).resolve()
            if not target_path.exists():
                continue

            if (target_path / "SKILL.md").exists():
                skill_name = entry.name or target_path.name
                if skill_name not in self.data.exclude:
                    tier_val = self.data.skills.get(skill_name, ProjectSkillInfo()).tier
                    found_skills[skill_name] = Skill(target_path, tier=tier_val)
            elif target_path.is_dir():
                for sub_dir in sorted(target_path.iterdir()):
                    if sub_dir.is_dir() and (sub_dir / "SKILL.md").exists():
                        skill_name = sub_dir.name
                        if skill_name not in self.data.exclude:
                            tier_val = self.data.skills.get(skill_name, ProjectSkillInfo()).tier
                            found_skills[skill_name] = Skill(sub_dir, tier=tier_val)

        self._cached_skills = found_skills
        return found_skills

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """指定された名前のスキルを取得します。"""
        skills = self.scan_skills()
        return skills.get(skill_name)

    def list_skills(self) -> list[Skill]:
        """検出されたすべてのスキルのリストを返します。"""
        return list(self.scan_skills().values())

    def register_skill(self, skill_name: str, tier: SkillTier | int = SkillTier.SANDBOX):
        """指定されたスキルの Tier を更新・登録し、永続化します（set_skill_tier のエイリアス）。"""
        self.set_skill_tier(skill_name, tier)

    def set_skill_tier(self, skill_name: str, tier: SkillTier | int):
        """指定されたスキルの Tier を更新し、永続化します。"""
        if self.data is None:
            self.load()

        tier_enum = SkillTier(tier) if isinstance(tier, int) else tier
        self.data.skills[skill_name] = ProjectSkillInfo(tier=tier_enum)
        self.save()

    def get_dependencies(self, skill_name: str) -> list[str]:
        """指定されたスキルの依存先スキル名一覧を取得します。"""
        skill = self.get_skill(skill_name)
        return skill.dependencies if skill else []

    def build_dependency_graph(self) -> dict[str, list[str]]:
        """全スキルの依存関係 DAG を構築します。"""
        skills = self.scan_skills()
        graph: dict[str, list[str]] = {}
        for name, skill in skills.items():
            graph[name] = skill.dependencies
        return graph

    def validate_dependency_graph(self) -> Tuple[bool, list[str]]:
        """依存関係グラフの整合性（存在しない依存先、循環依存）を検証します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()
        errors: list[str] = []

        # 1. 存在確認
        for name, deps in graph.items():
            for dep in deps:
                if dep not in skills:
                    errors.append(f"Skill '{name}' depends on non-existent skill '{dep}'.")

        # 2. 循環依存検知 (DFS)
        visited = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str, path: list[str]) -> bool:
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

    def get_dependents(self, skill_name: str) -> list[str]:
        """指定したスキルを直接依存している上位スキル名リスト（逆引き）を返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()
        dependents = []
        for parent, deps in graph.items():
            if skill_name in deps:
                dependents.append(parent)
        return sorted(dependents)

    def get_cascade_dependents(self, skill_name: str) -> list[str]:
        """指定したスキルが更新された際に、再テストが必要な依存先（逆依存先）リストをトポロジカル順で返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()
        
        # 逆グラフ構築
        reverse_graph: dict[str, list[str]] = {s: [] for s in skills}
        for parent, deps in graph.items():
            for d in deps:
                if d in reverse_graph:
                    reverse_graph[d].append(parent)

        # BFS で全下流ノードを探索
        dependents: list[str] = []
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

    def get_execution_order(self) -> list[str]:
        """依存関係 DAG に基づき、依存される側が先頭に来るトポロジカル実行順序リストを返します。"""
        skills = self.scan_skills()
        graph = self.build_dependency_graph()

        in_degree = {s: 0 for s in skills}
        # graph[u] は u が依存している先 (u -> v where u depends on v)
        # 実行順序としては v -> u
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

        # 孤立ノードや残りがある場合も追加
        for s in skills:
            if s not in order:
                order.append(s)

        return order
