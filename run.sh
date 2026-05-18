#!/usr/bin/env bash
cd "$(dirname "$0")"
PY=".venv/Scripts/python.exe"
if [[ ! -x "$PY" ]]; then
  echo ".venv がありません。README のセットアップを実行してください." >&2
  exit 1
fi
exec "$PY" app.py "$@"
