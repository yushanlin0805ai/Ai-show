#!/usr/bin/env bash
# 模式 B 一鍵渲染：合成影片＋透明圖卡層＋透明字幕層 → 切段 → cue list → 時間軸檔 → 自動檢查
# 用法（repo 根目錄）：bash .claude/skills/talking-head-broll/scripts/render-all.sh projects/<名稱> [--skip-composite]
# 時間：59 秒影片約 15 分鐘（合成 5 分、透明圖卡層 6 分、字幕層 2 分）
set -euo pipefail
P="${1:?用法：render-all.sh projects/<名稱>}"; shift || true
SKIP_COMPOSITE=0; [ "${1:-}" = "--skip-composite" ] && SKIP_COMPOSITE=1

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
PREP="$ROOT/.claude/skills/broll-video/scripts/prepare-composition.py"
HF="npx -y hyperframes@0.9.19"
NAME="$(basename "$P")"
cd "$ROOT"

export HYPERFRAMES_SKIP_SKILLS=1
if [ -z "${HYPERFRAMES_BROWSER_PATH:-}" ]; then
  for c in /opt/pw-browsers/chromium-*/chrome-linux*/chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" /usr/bin/google-chrome /usr/bin/chromium; do
    [ -x "$c" ] && export HYPERFRAMES_BROWSER_PATH="$c" && break
  done
fi

render() {  # $1 資料夾  $2.. render 參數
  local dir="$1"; shift
  (cd "$P/$dir" && $HF lint . | tail -1 && $HF render --fps 30 "$@" 2>&1 | grep -E "MB ·|rror" || true)
}

mkdir -p "$P/output/broll"
echo "▶ 1/6 準備素材與字幕"
python3 "$PREP" "$P"

if [ $SKIP_COMPOSITE -eq 0 ]; then
  echo "▶ 2/6 合成影片（原片＋動畫＋字幕）"
  render composition --output "../output/${NAME}-合成.mp4" --quality high
fi

echo "▶ 3/6 透明圖卡層"
python3 "$PREP" "$P" --mode overlay
render composition-overlay --format webm --output ../output/broll/overlay-full.webm

echo "▶ 4/6 透明字幕層"
python3 "$PREP" "$P" --mode captions
render composition-captions --format webm --output ../output/broll/captions.webm
cp "$P/storyboard/timing/transcript.srt" "$P/output/broll/captions.srt"

echo "▶ 5/6 切段、cue list、時間軸檔"
python3 "$HERE/split-broll.py" "$P"
python3 "$HERE/export-timeline.py" "$P"

echo "▶ 6/6 自動檢查"
python3 "$HERE/verify-output.py" "$P"
