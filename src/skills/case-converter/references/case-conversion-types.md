# ケース変換タイプのリファレンス

このドキュメントは、文字列のケース変換に使用される主要なタイプを定義し、それぞれの使用例を提供します。AIがユーザーにケース変換の概念を説明する際に参照してください。

---

## 1. 大文字 (Uppercase)

### 定義
すべてのアルファベット文字を大文字に変換します。数字や記号は変更されません。

### 例
- 入力: `hello world`
- 出力: `HELLO WORLD`

- 入力: `Python_Programming`
- 出力: `PYTHON_PROGRAMMING`

---

## 2. 小文字 (Lowercase)

### 定義
すべてのアルファベット文字を小文字に変換します。数字や記号は変更されません。

### 例
- 入力: `HELLO WORLD`
- 出力: `hello world`

- 入力: `Python_Programming`
- 出力: `python_programming`

---

## 3. キャメルケース (Camel Case)

### 定義
最初の単語は小文字で始まり、それ以降の各単語の最初の文字を大文字に変換し、単語間の区切り文字を削除します。

### 例
- 入力: `hello world`
- 出力: `helloWorld`

- 入力: `python programming language`
- 出力: `pythonProgrammingLanguage`

---

## 4. パスカルケース (Pascal Case)

### 定義
すべての単語の最初の文字を大文字に変換し、単語間の区切り文字を削除します。キャメルケースと似ていますが、最初の単語も大文字で始まります。

### 例
- 入力: `hello world`
- 出力: `HelloWorld`

- 入力: `python programming language`
- 出力: `PythonProgrammingLanguage`

---

## 5. スネークケース (Snake Case)

### 定義
すべてのアルファベット文字を小文字に変換し、単語間のスペースや区切り文字をアンダースコア (`_`) に置き換えます。

### 例
- 入力: `hello world`
- 出力: `hello_world`

- 入力: `Python Programming Language`
- 出力: `python_programming_language`

---

## 6. ケバブケース (Kebab Case)

### 定義
すべてのアルファベット文字を小文字に変換し、単語間のスペースや区切り文字をハイフン (`-`) に置き換えます。

### 例
- 入力: `hello world`
- 出力: `hello-world`

- 入力: `Python Programming Language`
- 出力: `python-programming-language`

---

## 7. タイトルケース (Title Case)

### 定義
各単語の最初の文字を大文字に変換し、それ以外の文字を小文字に変換します。通常、前置詞や冠詞などの短い単語は小文字のまま維持される場合がありますが、このスキルでは単純にすべての単語の最初の文字を大文字にします。

### 例
- 入力: `hello world`
- 出力: `Hello World`

- 入力: `python programming language`
- 出力: `Python Programming Language`

---

## 8. スペース区切り (Space Separated)

### 定義
文字列内の単語をスペースで区切られた形式に変換します。既存のケーススタイル（キャメルケース、スネークケースなど）から単語を抽出し、スペースで結合します。

### 例
- 入力: `helloWorld`
- 出力: `hello World`

- 入力: `python_programming_language`
- 出力: `python programming language`

- 入力: `HelloWorld`
- 出力: `Hello World`