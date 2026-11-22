#!/usr/bin/env bash
# 環境檢查：確認製作短影音需要的工具都就緒，缺什麼就列出來。
# 用法（在專案根目錄）：bash .claude/skills/broll-video/scripts/check-setup.sh
# 只檢查、不安裝。

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
OS="$(uname -s)"
missing=()
ok()   { printf "  \033[32m✓\033[0m %-22s %s\n" "$1" "$2"; }
bad()  { printf "  \033[31m✗\033[0m %-22s %s\n" "$1" "$2"; missing+=("$1|$3"); }
warn() { printf "  \033[33m!\033[0m %-22s %s\n" "$1" "$2"; }

echo "短影音工具包 — 環境檢查（$OS）"
echo

# 1. Node.js 22+（Hyperframes 需要）
if command -v node >/dev/null 2>&1; then
  v="$(node -v | sed 's/^v//')"; major="${v%%.*}"
  if [ "$major" -ge 22 ]; then ok "Node.js" "v$v"
  else bad "Node.js" "v$v（需要 22 以上）" "到 https://nodejs.org 安裝 22 LTS 以上，或 Mac：brew install node@22"; fi
else
  bad "Node.js" "沒有安裝" "到 https://nodejs.org 安裝 22 LTS 以上，或 Mac：brew install node@22"
fi

# 2. ffmpeg / ffprobe
for t in ffmpeg ffprobe; do
  if command -v "$t" >/dev/null 2>&1; then ok "$t" "$("$t" -version 2>/dev/null | head -1 | awk '{print $3}')"
  else bad "$t" "沒有安裝" "Mac：brew install ffmpeg ／ Windows：winget install ffmpeg ／ Linux：sudo apt install ffmpeg"; fi
done

# 3. Python 3 + faster-whisper（語音轉文字）
PY="$(command -v python3 || command -v python)"
if [ -n "$PY" ]; then
  ok "Python" "$("$PY" --version 2>&1 | awk '{print $2}')"
  if "$PY" -c "import faster_whisper" >/dev/null 2>&1; then
    ok "faster-whisper" "$("$PY" -c 'import faster_whisper;print(faster_whisper.__version__)' 2>/dev/null)"
  else
    bad "faster-whisper" "沒有安裝" "$PY -m pip install faster-whisper opencc-python-reimplemented"
  fi
  if "$PY" -c "import cv2; cv2.CascadeClassifier" >/dev/null 2>&1; then ok "OpenCV（找臉）" "$("$PY" -c 'import cv2;print(cv2.__version__)')"
  else warn "OpenCV（找臉）" "模式 B 才需要：$PY -m pip install \"opencv-python-headless<5\""; fi
  if "$PY" -c "import opencc" >/dev/null 2>&1; then ok "opencc（簡轉繁）" "已安裝"
  else warn "opencc（簡轉繁）" "沒有安裝（可選，會讓時間點對齊更準）：$PY -m pip install opencc-python-reimplemented"; fi
  # 模型是否已下載（第一次轉文字會自動下載約 3GB）
  if ls "${HF_HOME:-$HOME/.cache/huggingface}/hub" 2>/dev/null | grep -q faster-whisper; then
    ok "語音模型" "$(ls "${HF_HOME:-$HOME/.cache/huggingface}/hub" | grep faster-whisper | sed 's/models--Systran--//' | tr '\n' ' ')"
  else
    warn "語音模型" "尚未下載（第一次轉文字時會自動從 huggingface.co 下載 large-v3，約 3GB）"
  fi
else
  bad "Python" "沒有安裝" "到 https://www.python.org 安裝 Python 3.10 以上"
fi

# 4. 中文字型（repo 內附 Noto Sans TC）
FONT_OK=0
for w in NotoSansTC-Regular.otf NotoSansTC-Bold.otf NotoSansTC-Black.otf NotoColorEmoji.ttf; do [ -f "$ROOT/fonts/$w" ] && FONT_OK=$((FONT_OK+1)); done
if [ "$FONT_OK" -eq 4 ]; then ok "Noto Sans TC＋Emoji" "fonts/ 內 4 個字型檔齊全"
else bad "Noto Sans TC＋Emoji" "fonts/ 內缺字型檔（$FONT_OK/4）" "重新 git pull，或從 https://github.com/notofonts/noto-cjk 下載 Sans/SubsetOTF/TC 放進 fonts/"; fi
if command -v fc-list >/dev/null 2>&1; then
  if fc-list | grep -qi "Noto Sans TC\|Noto Sans CJK TC"; then ok "系統字型" "已安裝 Noto Sans TC"
  else warn "系統字型" "系統沒裝 Noto Sans TC（不影響：畫面會用 fonts/ 內的檔案）"; fi
fi

# 5. Hyperframes（HTML → 影片渲染）
if command -v node >/dev/null 2>&1; then
  if command -v hyperframes >/dev/null 2>&1; then
    ok "Hyperframes" "$(hyperframes --version 2>/dev/null | head -1)（全域安裝）"
  elif [ -x "$ROOT/node_modules/.bin/hyperframes" ]; then
    ok "Hyperframes" "$("$ROOT/node_modules/.bin/hyperframes" --version 2>/dev/null | head -1)（專案內）"
  else
    latest="$(npm view hyperframes version 2>/dev/null)"
    warn "Hyperframes" "未預先安裝（渲染時用 npx hyperframes 自動下載${latest:+，最新版 $latest}）"
  fi
fi

# 5b. GSAP（動畫函式庫，從 npm 安裝，不走 CDN）
if [ -f "$ROOT/node_modules/gsap/dist/gsap.min.js" ]; then ok "GSAP" "node_modules/gsap"
else bad "GSAP" "尚未安裝" "在 repo 根目錄執行：npm install"; fi

# 6. 渲染用的 Chrome
if [ -n "$HYPERFRAMES_BROWSER_PATH" ] && [ -x "$HYPERFRAMES_BROWSER_PATH" ]; then
  ok "Chrome" "$HYPERFRAMES_BROWSER_PATH（HYPERFRAMES_BROWSER_PATH）"
else
  found=""
  for p in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" /opt/pw-browsers/chromium /usr/bin/google-chrome /usr/bin/chromium /usr/bin/chromium-browser; do
    [ -e "$p" ] && found="$p" && break
  done
  if [ -n "$found" ]; then ok "Chrome" "$found"
  else warn "Chrome" "找不到系統 Chrome（渲染時可執行 npx hyperframes browser ensure 自動下載）"; fi
fi

echo
if [ ${#missing[@]} -eq 0 ]; then
  echo "全部就緒 ✓  可以開始製作。"
  echo "（渲染前可再執行 npx hyperframes doctor 做完整檢查）"
  exit 0
else
  echo "缺少 ${#missing[@]} 項，請依序安裝："
  for m in "${missing[@]}"; do
    printf "  • %s：%s\n" "${m%%|*}" "${m#*|}"
  done
  exit 1
fi
