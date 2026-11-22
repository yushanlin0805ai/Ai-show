#!/usr/bin/env python3
"""把共用素材與變數填進 Hyperframes 專案（可重複執行）。

用法：
  python3 prepare-composition.py projects/<影片名稱> [--html composition/index.html] [--mode composite|overlay|captions]

會做的事：
  1. 複製 fonts/（Noto Sans TC、Noto Color Emoji）→ composition/fonts/
  2. 複製 node_modules/gsap/dist/gsap.min.js → composition/vendor/（沒有就提示 npm install）
  3. 複製 inputs/ 的音檔與影片 → composition/（檔名不變）
  4. 依 storyboard/timing/transcript.srt 產生字幕，填進 HTML 的
     <!-- CAPTIONS:BEGIN --> … <!-- CAPTIONS:END --> 之間
  5. 依 project.json 的 cta 變數，把 HTML 裡 data-cta="question|keyword|action|action-tail"
     元素的文字換成變數值
  6. --mode（模式 B 用）：composite＝原片＋全部（就是 index.html）；
     overlay＝透明背景、只有動畫（給 B-roll）；captions＝只有字幕（透明）。
     overlay／captions 會產生 composition-overlay/、composition-captions/ 資料夾（不進 Git），
     在那個資料夾裡 render --format webm。

project.json 可選的字幕設定（沒有就用通用預設；正式品牌請在 project.json 寫好）：
  "caption": {"px": 60, "line_units": 16, "keywords": ["牡羊座", "副業"]}
  關鍵字會包成 <span class="kw">（橘黃、1.75 倍），字寬計算也把關鍵字算 1.75 倍；一則最多 2 個。

這些複製進來的檔案都在 .gitignore 裡，不會進 Git。
"""
import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CTA = {
    "question": "想知道自己的卡點在哪裡嗎？",
    "action": "留言「測驗」，領取免費測驗！",
    "keyword": "測驗",
}
FONTS = ["NotoSansTC-Regular.otf", "NotoSansTC-Bold.otf", "NotoSansTC-Black.otf", "NotoColorEmoji.ttf"]
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".aac"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
KW_SCALE = 1.75
MAX_KW_PER_CUE = 2
# 兩則字幕間隔小於這個秒數，前一則就延長到下一則開始（避免字幕閃爍）
GAP_BRIDGE = 1.0
# 最後一則／間隔大的字幕，講完後多留多久
TAIL_HOLD = 0.4
# 字幕字級與一行可放的字寬（字幕框 928px ÷ 69px）
CAPTION_PX = 69
LINE_CHARS = 13.4


def parse_srt(path):
    cues = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        s = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        cues.append([s, e, " ".join(lines[2:])])
    for i, c in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else None
        if nxt is not None and nxt - c[1] < GAP_BRIDGE:
            c[1] = nxt
        else:
            c[1] = c[1] + TAIL_HOLD
    return cues


def replace_block(text, name, body):
    pat = re.compile(rf"(<!-- {name}:BEGIN -->)(.*?)(\s*<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        sys.exit(f"HTML 裡找不到 <!-- {name}:BEGIN --> / <!-- {name}:END --> 標記")
    return pat.sub(lambda m: m.group(1) + body + m.group(3), text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--html", default="composition/index.html")
    ap.add_argument("--mode", choices=["composite", "overlay", "captions"], help="模式 B：輸出哪一種畫面")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    comp_html = proj / args.html
    comp = comp_html.parent

    # 1. 字型
    (comp / "fonts").mkdir(parents=True, exist_ok=True)
    for f in FONTS:
        src = ROOT / "fonts" / f
        if not src.exists():
            sys.exit(f"缺字型 {src}，請執行 check-setup.sh")
        dst = comp / "fonts" / f
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)

    # 2. GSAP
    gsap = ROOT / "node_modules/gsap/dist/gsap.min.js"
    if not gsap.exists():
        sys.exit("找不到 GSAP，請在 repo 根目錄執行：npm install")
    (comp / "vendor").mkdir(exist_ok=True)
    shutil.copy2(gsap, comp / "vendor/gsap.min.js")

    # 3. 音檔與影片
    for a in (proj / "inputs").iterdir():
        if a.suffix.lower() in AUDIO_EXT | VIDEO_EXT and not (comp / a.name).exists():
            shutil.copy2(a, comp / a.name)

    text = comp_html.read_text(encoding="utf-8")
    cfg = {}
    pj = proj / "project.json"
    if pj.exists():
        cfg = json.loads(pj.read_text(encoding="utf-8"))
    cap_cfg = cfg.get("caption", {})
    px = cap_cfg.get("px", CAPTION_PX)
    line_units = cap_cfg.get("line_units", LINE_CHARS)
    keywords = sorted(cap_cfg.get("keywords", []), key=len, reverse=True)

    # 4. 字幕
    srt = proj / "storyboard/timing/transcript.srt"
    cues = parse_srt(srt)
    def mark_keywords(t):
        """找出關鍵字位置（長的優先、不重疊、最多 MAX_KW_PER_CUE 個），回傳 [(文字, 是否關鍵字)]"""
        taken, spans = set(), []
        for k in keywords:
            for m in re.finditer(re.escape(k), t):
                rng = set(range(m.start(), m.end()))
                if rng & taken or len(spans) >= MAX_KW_PER_CUE:
                    continue
                taken |= rng
                spans.append((m.start(), m.end()))
        spans.sort()
        parts, i = [], 0
        for a, b in spans:
            if a > i:
                parts.append((t[i:a], False))
            parts.append((t[a:b], True))
            i = b
        if i < len(t):
            parts.append((t[i:], False))
        return parts

    def cue_tag(s, e, t):
        t = t.rstrip("，、；：,。. ")
        parts = mark_keywords(t)
        # 一行放不下就等比例縮小字級，避免換行（關鍵字算 1.75 倍寬）
        w = sum((KW_SCALE if kw else 1) * sum(0.5 if ch.isascii() else 1 for ch in seg) for seg, kw in parts)
        style = f' style="font-size:{int(px * line_units / w)}px"' if w > line_units else ""
        inner = "".join(f'<span class="kw">{html.escape(seg)}</span>' if kw else html.escape(seg) for seg, kw in parts)
        return f'        <p data-s="{s:.2f}" data-e="{e:.2f}"{style}>{inner}</p>'
    body = "\n" + "\n".join(cue_tag(s, e, t) for s, e, t in cues)
    text = replace_block(text, "CAPTIONS", body)

    # 5. CTA
    cta = {**DEFAULT_CTA, **cfg.get("cta", {})}
    tail = cta["action"].split("，", 1)[1] if "，" in cta["action"] else cta["action"]
    values = {"question": cta["question"], "keyword": cta["keyword"], "action": cta["action"], "action-tail": tail}
    for k, v in values.items():
        text = re.sub(rf'(<[^>]*data-cta="{k}"[^>]*>)(.*?)(</)', lambda m: m.group(1) + html.escape(v) + m.group(3), text)

    # 6. 模式：index.html 永遠是完整版（composite）。overlay／captions 另外產生資料夾
    #    composition-<模式>/，直接把不需要的層從 HTML 拿掉（Hyperframes 會另外合成 <video>，
    #    只用 CSS 隱藏擋不住），字型／GSAP／樣式用捷徑指回 composition/。
    comp_html.write_text(text, encoding="utf-8")
    out_dir = comp
    if args.mode in ("overlay", "captions"):
        v = text
        v = re.sub(r"\s*<video\b[^>]*>.*?</video>", "", v, flags=re.S)            # 原片
        v, n = re.subn(r'class="mode-(composite|overlay|captions)"', f'class="mode-{args.mode}"', v, count=1)
        if not n:
            sys.exit('根元素需要 class="mode-composite"（透明版本靠它把背景改成透明）')
        if args.mode == "overlay":
            v = re.sub(r'\s*<div id="captions".*?<!-- CAPTIONS:END -->\s*</div>', "", v, flags=re.S)
        else:
            v = re.sub(r"\s*<section\b.*?</section>", "", v, flags=re.S)
        out_dir = comp.parent / f"{comp.name}-{args.mode}"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "index.html").write_text(v, encoding="utf-8")
        for f in ("hyperframes.json", "meta.json", "package.json"):
            if (comp / f).exists():
                shutil.copy2(comp / f, out_dir / f)
        for d in ("fonts", "vendor", "styles", "assets"):
            link = out_dir / d
            if (comp / d).exists() and not link.exists():
                link.symlink_to(Path("..") / comp.name / d)

    mode = f"，模式 {args.mode}（{out_dir.name}/）" if args.mode else ""
    print(f"完成：{len(cues)} 則字幕、CTA「{cta['keyword']}」、字型與 GSAP 已就緒{mode} → {comp}")

if __name__ == "__main__":
    main()
