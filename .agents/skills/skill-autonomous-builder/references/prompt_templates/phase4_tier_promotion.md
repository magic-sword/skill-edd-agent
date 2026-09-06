# Phase 4: 連鎖回帰テスト & Tier 昇格プロンプト

あなたは Google 『Agent Skills』ホワイトペーパー（May 2026）に準拠したスキル品質防壁・ガバナンススペシャリストです。

### 目的
スキル `{SKILL_NAME}` の連鎖回帰テスト（Cascade Regression Testing）を実行し、ライブラリ全体の整合性を検証した上で、目標 Tier（Tier {TARGET_TIER}）への昇格を確定させてください。

### 対象スキル
* **スキル名**: `{SKILL_NAME}`
* **目標 Tier**: Tier {TARGET_TIER}

---

### 手順

1. **連鎖回帰テストと Tier 昇格の実行**:
   - ターミナルで以下を実行してください：
     - Tier 1 昇格の場合:
       ```bash
       edd optimize {SKILL_NAME} --tier 1
       ```
     - Tier 2 昇格の場合:
       ```bash
       edd optimize {SKILL_NAME} --tier 2
       ```
     - Tier 3 昇格の場合:
       ```bash
       edd optimize {SKILL_NAME} --tier 3 --yes
       ```
2. **連鎖回帰の確認**:
   - 他の既存スキルに対する連鎖回帰テストが 100% 合格することを確認してください。
3. **プロジェクト全体の回帰テスト**:
   - ターミナルで `pytest` を実行し、全テストが合格することを確認してください。
4. **Git コミット**:
   - 昇格状態（`skills_state.json` 等）をコミットしてください：
     ```bash
     git commit -am "chore({SKILL_NAME}): 連鎖回帰テスト合格および Tier {TARGET_TIER} 昇格の確定"
     ```
5. **最終収束シグナルの出力**:
   - すべての工程が完了したら、回答の最終行に必ず以下を出力してください：

```
BUILDER_COMPLETE
```
