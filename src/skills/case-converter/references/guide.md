# Case Converter Reference Guide

## 対応ケース形式一覧

| 形式名 (`--to` / `-f`) | 説明 | 入力例 | 出力例 |
| :--- | :--- | :--- | :--- |
| `camel` / `camelCase` | 先頭小文字、単語区切りを大文字 | `hello_world_test` | `helloWorldTest` |
| `snake` / `snake_case` | 全小文字、アンダースコア区切り | `helloWorldTest` | `hello_world_test` |
| `pascal` / `PascalCase` | 単語先頭を大文字 | `hello_world_test` | `HelloWorldTest` |
| `kebab` / `kebab-case` | 全小文字、ハイフン区切り | `helloWorldTest` | `hello-world-test` |
| `constant` / `CONSTANT_CASE` | 全大文字、アンダースコア区切り | `helloWorldTest` | `HELLO_WORLD_TEST` |
| `title` / `Title Case` | 単語先頭を大文字、スペース区切り | `hello_world_test` | `Hello World Test` |
| `upper` / `UPPERCASE` | 単純な大文字変換 | `hello world` | `HELLO WORLD` |
| `lower` / `lowercase` | 単純な小文字変換 | `HELLO WORLD` | `hello world` |

## 動作仕様とエッジケース
- 連続する記号（`__`, `--`, 空白）は単一の区切りとして正規化されます。
- アクロニム（略語、例: `HTMLParser`, `getUserID`）は単語境界を考慮して適切に分割されます。
- 複数行テキストは行ごとに変換されます。
