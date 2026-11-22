#!/usr/bin/env python3
"""模式 B：把整段透明動畫（overlay-full.webm）依分鏡切成一段段 B-roll，並寫出 cue list。

用法：
  python3 .agents/skills/talking-head-broll/scripts/split-broll.py projects/<影片名稱>

讀 project.json 的 "segments"：
  [{"id": "broll-01", "start": 0, "end": 4.27, "kind": "overlay", "place": "臉上方圖卡區", "line": "口播…"},
   {"id": "cut-01",   "start": 4.27, "end": 7.85, "kind": "cutaway", ...}]
  kind = overlay（透明疊加 → .webm 含透明＋ .mov ProRes 4444）
       | cutaway（全螢幕插畫 → .mp4）

輸入：output/broll/overlay-full.webm（render-all.sh 會自動產生）
輸出：output/broll/<id>.webm／.mov／.mp4、output/broll/cue-list.md（也複製到 storyboard/cue-list.md）
"""
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg 失敗：{' '.join(cmd)}\n{r.stderr[-800:]}")


def main():
    proj = Path(sys.argv[1]).resolve()
    cfg = json.loads((proj / "project.json").read_text(encoding="utf-8"))
    segs = cfg.get("segments") or sys.exit("project.json 沒有 segments")
    out = proj / "output/broll"
    src = out / "overlay-full.webm"
    if not src.exists():
        sys.exit(f"找不到 {src}，請先渲染 overlay 模式")

    for s in segs:
        ss, dur = f"{s['start']:.3f}", f"{s['end'] - s['start']:.3f}"
        # 透明 WebM 要用 libvpx-vp9 解碼才讀得到 alpha
        base = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-ss", ss, "-t", dur, "-i", str(src), "-an"]
        if s["kind"] == "overlay":
            run(base + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "18",
                        "-auto-alt-ref", "0", "-metadata:s:v:0", "alpha_mode=1", str(out / f"{s['id']}.webm")])
            run(base + ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out / f"{s['id']}.mov")])
        else:
            run(base + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-r", "30", str(out / f"{s['id']}.mp4")])
        print(f"  ✓ {s['id']}  {s['start']:.2f}–{s['end']:.2f}s")

    rows = ["# Cue list：第幾秒放哪一段", "",
            f"原片：`{cfg.get('source', {}).get('file', '')}`（字幕另有 `captions.webm` 透明軌與 `captions.srt`）", "",
            "| 檔案 | 放在原片 | 長度 | 類型 | 位置 | 對應口播 |", "|---|---|---|---|---|---|"]
    for s in segs:
        files = f"{s['id']}.webm／.mov" if s["kind"] == "overlay" else f"{s['id']}.mp4"
        kind = "透明疊加（講者照常）" if s["kind"] == "overlay" else "全螢幕插畫（蓋掉講者）"
        rows.append(f"| {files} | {s['start']:.2f}–{s['end']:.2f}s | {s['end'] - s['start']:.1f}s | {kind} | {s.get('place', '')} | {s.get('line', '')} |")
    rows += ["", "剪輯方式：把原片放最底層，B-roll 放上一層、對齊上表的起點秒數，字幕軌放最上層。",
             "透明疊加段用 .mov（Premiere／DaVinci）或 .webm（CapCut、瀏覽器）；全螢幕插畫段直接蓋在原片上即可。"]
    text = "\n".join(rows) + "\n"
    (out / "cue-list.md").write_text(text, encoding="utf-8")
    (proj / "storyboard/cue-list.md").write_text(text, encoding="utf-8")
    print(f"完成：{len(segs)} 段 → {out}")


if __name__ == "__main__":
    main()
