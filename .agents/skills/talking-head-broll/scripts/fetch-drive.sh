#!/usr/bin/env bash
# 從 Google Drive 下載影片（檔案要先設成「知道連結的人都能檢視」）。
# 用法：bash fetch-drive.sh <Drive 分享連結或檔案 ID> <輸出路徑，例如 projects/xxx/inputs/source.mp4>
# 雲端環境需要允許 drive.google.com、drive.usercontent.google.com 兩個網址。
set -euo pipefail
[ $# -eq 2 ] || { echo "用法：bash fetch-drive.sh <連結或檔案ID> <輸出路徑>"; exit 2; }

ID="$1"
# 從 https://drive.google.com/file/d/<ID>/view?... 取出 ID
if [[ "$ID" == *"/d/"* ]]; then ID="${ID#*/d/}"; ID="${ID%%/*}"; fi
if [[ "$ID" == *"id="* ]]; then ID="${ID#*id=}"; ID="${ID%%&*}"; fi
OUT="$2"
mkdir -p "$(dirname "$OUT")"

URL="https://drive.usercontent.google.com/download?id=${ID}&export=download&confirm=t"
echo "下載中：$ID → $OUT"
if ! curl -sSfL --retry 3 --max-time 1800 -o "$OUT" "$URL"; then
  echo "✗ 下載失敗。請確認："
  echo "  1. Drive 檔案已設為「知道連結的人都能檢視」"
  echo "  2. 網路允許 drive.google.com 與 drive.usercontent.google.com（雲端環境的網路設定）"
  exit 1
fi

# Drive 權限不對時會回一個 HTML 頁面，而不是影片
if head -c 512 "$OUT" | grep -qi "<html"; then
  rm -f "$OUT"
  echo "✗ 拿到的是網頁不是影片：檔案多半還沒開「知道連結的人都能檢視」。"
  exit 1
fi

echo "✓ 已下載 $(du -h "$OUT" | cut -f1)"
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate:format=duration -of compact "$OUT"
echo "提醒：用完可以把 Drive 的分享設定關掉。"
