#!/bin/bash
# Taigi-whisper-Mac 啟動腳本
# 第一次執行會自動建立虛擬環境並安裝所有套件（需要幾分鐘）

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv"

# 建立虛擬環境（Python 3.11）
if [ ! -d "$VENV" ]; then
    echo "=== 第一次執行，建立虛擬環境（Python 3.11）..."
    uv venv --python 3.11 "$VENV"
fi

# 安裝/更新套件
echo "=== 確認套件已安裝..."
uv pip install --python "$VENV/bin/python" -r "$SCRIPT_DIR/requirements.txt" -q

echo "=== 啟動 Taigi-whisper-Mac..."
"$VENV/bin/python" "$SCRIPT_DIR/taigi_whisper_mac.py"
