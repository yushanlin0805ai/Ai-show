#!/usr/bin/env bash
# 雲端環境安裝腳本（Claude Code 的 Setup script／ChatGPT Codex 的 Setup script 都貼這一行）：
#   bash setup.sh
# 裝好動畫渲染與語音辨識需要的東西。已經裝過的會略過，重跑沒關係。
set -u
cd "$(dirname "$0")"

echo "== 1/4 前端套件（GSAP）"
npm install --no-audit --no-fund || echo "!! npm install 失敗"

echo "== 2/4 動畫渲染工具 Hyperframes（固定版本）與瀏覽器"
npx -y hyperframes@0.9.19 --version || echo "!! Hyperframes 安裝失敗"
npx -y hyperframes@0.9.19 doctor || true

echo "== 3/4 語音辨識與影像工具（Python）"
PIP="python3 -m pip install --quiet"
$PIP faster-whisper opencc-python-reimplemented "opencv-python-headless<5" 2>/dev/null \
  || $PIP --break-system-packages faster-whisper opencc-python-reimplemented "opencv-python-headless<5" \
  || echo "!! Python 套件安裝失敗"
command -v ffmpeg >/dev/null || { (sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg) 2>/dev/null || apt-get install -y -qq ffmpeg 2>/dev/null || echo "!! 請安裝 ffmpeg"; }

echo "== 4/4 先下載語音辨識模型（約 3GB，只有第一次）"
python3 - <<'EOF' || echo "!! 模型下載失敗，第一次做影片時會再試"
from faster_whisper import WhisperModel
WhisperModel("large-v3", device="cpu", compute_type="int8")
print("語音模型 OK")
EOF

echo "== 檢查"
bash .claude/skills/broll-video/scripts/check-setup.sh || true
