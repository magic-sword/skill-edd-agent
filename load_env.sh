#!/bin/bash
# .env および .devcontainer/.env から環境変数を読み込んでエクスポートするスクリプトです。
#
# 使い方:
#   source load_env.sh
#   または
#   . load_env.sh

load_env() {
  local env_files=(".env" ".devcontainer/.env")
  local loaded_any=false

  for file in "${env_files[@]}"; do
    if [ -f "$file" ]; then
      echo "Loading environment variables from $file..."
      while IFS= read -r line || [ -n "$line" ]; do
        # 空行やコメント行をスキップ
        if [[ ! "$line" =~ ^[[:space:]]*# && "$line" =~ = ]]; then
          # 前後の空白と引用符を除去して export
          local key=$(echo "$line" | cut -d'=' -f1 | xargs)
          local val=$(echo "$line" | cut -d'=' -f2- | xargs | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
          export "$key"="$val"
          loaded_any=true
        fi
      done < "$file"
    fi
  done

  if [ "$loaded_any" = true ]; then
    echo "Environment variables loaded successfully."
  else
    echo "No .env or .devcontainer/.env files found, or files were empty."
  fi
}

load_env
