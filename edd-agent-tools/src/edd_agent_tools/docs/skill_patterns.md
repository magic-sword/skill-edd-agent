# Skill Patterns & Architecture Types

All skills should be categorized into one of four standard architectural patterns:

## 1. Workflow-Based (`workflow`)
- **Best for**: Sequential multi-step processes with conditional logic.
- **Structure**: Overview ➔ Workflow Decision Tree ➔ Step 1 ➔ Step 2 ...
- **Key Element**: Explicit Decision Tree (`If condition ➔ Then action`).
- **Example**: `code-refactorer`, `pr-review-pipeline`.

## 2. Task-Based (`task_based`)
- **Best for**: Collections of standalone tools or utility operations.
- **Structure**: Overview ➔ Quick Start ➔ Task 1 ➔ Task 2 ...
- **Key Element**: Direct command / tool invocation catalog.
- **Example**: `pdf-tools`, `image-converter`.

## 3. Reference/Guidelines (`reference`)
- **Best for**: Domain knowledge, coding standards, brand guidelines, or policies.
- **Structure**: Overview ➔ Guidelines ➔ Specifications ➔ Best Practices.
- **Key Element**: `references/` files for deep-dive documentation.
- **Example**: `brand-guidelines`, `security-checklist`.

## 4. Capabilities-Based (`capabilities`)
- **Best for**: Complex integrated multi-module systems.
- **Structure**: Overview ➔ Core Capabilities ➔ 1. Capability A ➔ 2. Capability B ...
- **Key Element**: Interrelated operations combining scripts, references, and assets.
- **Example**: `mcp-builder`, `artifacts-builder`.
