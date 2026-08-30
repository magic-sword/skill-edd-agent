# edd-agent-tools 開発・貢献ガイドライン (Contributing Guide)

本プロジェクトへ貢献（コードの修正、ドキュメントの更新、新規スキルの追加など）してくださる開発者の皆様へ、開発フローと一貫した品質を維持するための設計思想・ドキュメント規約を定義します。

---

## 1. 開発環境のセットアップ

本パッケージの開発を行う際は、編集可能モード (Editable Mode) でインストールしてパスを通してください。

```bash
# リポジトリルートで実行
pip install -e .
```

詳細なセットアップ手順や MCP サーバーの起動手順については、[SETUP.md](SETUP.md) を参照してください。

---

---

## 2. 設計思想・開発ルールの遵守 (Single Source of Truth)

本プロジェクトにおける「README, SETUP, AGENTS.md, docs/ の役割分担」および「GoogleスタイルDocstringの適用とWhy（背景思想）の完全分離」といった厳密なドキュメント・コーディング規約は、パッケージ内蔵の **[AGENTS.md](src/edd_agent_tools/AGENTS.md)** に一元管理（シングルソース）されています。

人間が開発に携わる場合も、AIエージェントがコードを生成する場合も、真実のソースである上記の **[AGENTS.md](src/edd_agent_tools/AGENTS.md)** を一読し、記述ルールとシステム制約を厳密に遵守してください。

