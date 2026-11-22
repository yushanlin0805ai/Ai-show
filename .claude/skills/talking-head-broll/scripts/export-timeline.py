#!/usr/bin/env python3
"""依 project.json 的 segments 產生剪輯軟體時間軸檔（FCPXML 1.10）。

用法：
  python3 export-timeline.py projects/<名稱> [--media-root <素材資料夾在你電腦上的路徑>]

時間軸內容（1080×1920、30fps）：
  主軌：原片（含聲音）
  第 1 層：每段 B-roll，放在 cue list 的起點秒數
           - 透明疊加段用 broll-xx.mov（ProRes 4444，含透明；DaVinci／Final Cut 都讀得到）
           - 全螢幕插畫段用 cut-xx.mp4
  字幕：另外匯入 captions.srt（各軟體都支援匯入 SRT，比放進時間軸檔可靠）

匯入：
  DaVinci Resolve：檔案 → 匯入 → 時間軸（Timeline）→ 選 .fcpxml
  Final Cut Pro：檔案 → 匯入 → XML
  Premiere Pro：不支援 FCPXML。先用 DaVinci 匯入後「匯出 → 時間軸 → FCP 7 XML」，再給 Premiere 開；
                或直接照 cue-list.md 擺。

--media-root：檔案在你電腦上的資料夾（裡面要有原片與 broll/ 的檔案）。不給就用這台機器上的實際路徑；
              路徑不對時，剪輯軟體會要求「重新連結（Relink）」，指到素材資料夾即可。
輸出：output/<名稱>.fcpxml
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import quoteattr

FPS = 30


def t(sec):
    """秒數 → FCPXML 的有理數時間（對齊到格）。"""
    return f"{round(sec * FPS)}/{FPS}s"


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--media-root", help="你電腦上放素材的資料夾（原片與 broll/ 都在裡面）")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    cfg = json.loads((proj / "project.json").read_text(encoding="utf-8"))
    segs = cfg.get("segments") or sys.exit("project.json 沒有 segments")
    src = proj / cfg.get("source", {}).get("file", "")
    if not src.is_file():
        sys.exit(f"找不到原片 {src}")
    broll = proj / "output/broll"
    name = proj.name

    def url(local: Path, rel: str):
        if args.media_root:
            p = Path(args.media_root) / rel
            return "file://" + quote(p.as_posix())
        return "file://" + quote(local.resolve().as_posix())

    src_dur = duration(src)
    assets, clips = [], []
    assets.append(f'<asset id="src" name={quoteattr(src.name)} start="0s" duration="{t(src_dur)}" hasVideo="1" hasAudio="1" '
                  f'format="fmt" audioSources="1" audioChannels="2" audioRate="48000">'
                  f'<media-rep kind="original-media" src={quoteattr(url(src, src.name))}/></asset>')
    for i, s in enumerate(segs):
        f = broll / (f"{s['id']}.mov" if s["kind"] == "overlay" else f"{s['id']}.mp4")
        if not f.exists():
            sys.exit(f"找不到 {f}，請先執行 split-broll.py")
        d = duration(f) or (s["end"] - s["start"])
        aid = f"b{i}"
        assets.append(f'<asset id="{aid}" name={quoteattr(f.name)} start="0s" duration="{t(d)}" hasVideo="1" format="fmt">'
                      f'<media-rep kind="original-media" src={quoteattr(url(f, "broll/" + f.name))}/></asset>')
        length = min(d, s["end"] - s["start"])
        clips.append(f'<asset-clip ref="{aid}" lane="1" offset="{t(s["start"])}" start="0s" duration="{t(length)}" '
                     f'name={quoteattr(s["id"])}/>')

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
  <resources>
    <format id="fmt" name="FFVideoFormatRateUndefined" frameDuration="1/{FPS}s" width="1080" height="1920" colorSpace="1-1-1 (Rec. 709)"/>
    {chr(10).join("    " + a for a in assets).strip()}
  </resources>
  <library>
    <event name={quoteattr(name)}>
      <project name={quoteattr(cfg.get("title", name))}>
        <sequence format="fmt" duration="{t(src_dur)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
          <spine>
            <asset-clip ref="src" offset="0s" start="0s" duration="{t(src_dur)}" name={quoteattr(src.name)} tcFormat="NDF">
              {chr(10).join("              " + c for c in clips).strip()}
            </asset-clip>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
'''
    out = proj / "output" / f"{name}.fcpxml"
    out.write_text(xml, encoding="utf-8")
    print(f"完成：{out}（原片＋{len(clips)} 段 B-roll；字幕請另外匯入 output/broll/captions.srt）")


if __name__ == "__main__":
    main()
