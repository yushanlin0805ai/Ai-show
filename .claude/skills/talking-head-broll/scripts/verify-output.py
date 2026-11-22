#!/usr/bin/env python3
"""交付前自動檢查（模式 B 輸出）。

用法：
  python3 verify-output.py projects/<名稱> [--composite output/<名稱>-合成.mp4]

檢查：
  1. 合成影片：1080×1920、30fps、長度和原片差 < 0.1 秒、有聲音
  2. 每段 B-roll 檔案存在、長度符合 segments
  3. 透明疊加段（.webm）：中間那格真的透明（透明像素 ≥ 30%）
  4. 臉部安全區（project.json 的 face_zone）：透明疊加段中間那格，安全區內「不透明像素」的比例
     ≤ 1% 通過、1～5% 警告（多半是邊緣的字或結論條）、> 5% 失敗
  5. 產生 output/qa/facezone-check.jpg：合成影片每段中間一格＋紅框（含講者臉，不進 Git）
結束碼：有失敗就是 1。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    return json.loads(out or "{}")


def alpha_frame(webm, at):
    """取一格 RGBA（透明 WebM 要用 libvpx-vp9 解碼）。"""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-c:v", "libvpx-vp9", "-ss", f"{at:.3f}", "-i", str(webm),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True).stdout
    if len(raw) != 1080 * 1920 * 4:
        return None
    return np.frombuffer(raw, dtype=np.uint8).reshape(1920, 1080, 4)[:, :, 3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--composite")
    args = ap.parse_args()
    proj = Path(args.project).resolve()
    cfg = json.loads((proj / "project.json").read_text(encoding="utf-8"))
    segs, zone = cfg.get("segments", []), cfg.get("face_zone")
    src = proj / cfg.get("source", {}).get("file", "")
    comp = Path(args.composite) if args.composite else next((proj / "output").glob("*合成.mp4"), None)
    rows, fail = [], False

    def add(item, ok, note):
        nonlocal fail
        mark = {"ok": "✓", "warn": "⚠", "fail": "✗"}[ok]
        fail |= ok == "fail"
        rows.append(f"| {mark} | {item} | {note} |")

    # 1. 合成影片
    if comp and comp.exists():
        p = probe(comp)
        v = next((s for s in p.get("streams", []) if s["codec_type"] == "video"), {})
        has_a = any(s["codec_type"] == "audio" for s in p.get("streams", []))
        d = float(p.get("format", {}).get("duration", 0))
        sd = float(probe(src).get("format", {}).get("duration", 0)) if src.exists() else d
        ok = v.get("width") == 1080 and v.get("height") == 1920 and v.get("r_frame_rate") == "30/1" and abs(d - sd) < 0.1 and has_a
        add(f"合成影片 {comp.name}", "ok" if ok else "fail",
            f"{v.get('width')}×{v.get('height')}、{v.get('r_frame_rate')}、{d:.2f}s（原片 {sd:.2f}s）、{'有' if has_a else '沒有'}聲音")
    else:
        add("合成影片", "warn", "找不到（沒做合成就略過）")

    # 2～4. 每段 B-roll
    broll = proj / "output/broll"
    for s in segs:
        want = s["end"] - s["start"]
        f = broll / (f"{s['id']}.webm" if s["kind"] == "overlay" else f"{s['id']}.mp4")
        if not f.exists():
            add(s["id"], "fail", f"缺檔 {f.name}")
            continue
        d = float(probe(f).get("format", {}).get("duration", 0))
        if abs(d - want) > 0.15:
            add(s["id"], "fail", f"長度 {d:.2f}s，應為 {want:.2f}s")
            continue
        if s["kind"] != "overlay":
            add(s["id"], "ok", f"全螢幕插畫 {d:.2f}s")
            continue
        a = alpha_frame(f, want / 2)
        if a is None:
            add(s["id"], "fail", "讀不到透明通道")
            continue
        transparent = (a == 0).mean() * 100
        if transparent < 30:
            add(s["id"], "fail", f"透明只有 {transparent:.0f}%（背景可能沒設透明）")
            continue
        note = f"{d:.2f}s、透明 {transparent:.0f}%"
        if zone:
            z = a[zone["y0"]:zone["y1"], zone["x0"]:zone["x1"]]
            cover = (z > 128).mean() * 100
            level = "ok" if cover <= 1 else "warn" if cover <= 5 else "fail"
            note += f"、臉部安全區被蓋住 {cover:.1f}%"
            add(s["id"], level, note)
        else:
            add(s["id"], "warn", note + "、沒有 face_zone（先跑 face-zone.py）")

    # 5. 合成影片抽格＋紅框
    if comp and comp.exists() and zone and segs:
        qa = proj / "output/qa"
        qa.mkdir(parents=True, exist_ok=True)
        tiles = []
        for i, s in enumerate(segs):
            png = qa / f"_f{i}.png"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{(s['start'] + s['end']) / 2:.2f}", "-i", str(comp),
                            "-frames:v", "1", "-vf",
                            f"drawbox=x={zone['x0']}:y={zone['y0']}:w={zone['x1'] - zone['x0']}:h={zone['y1'] - zone['y0']}:color=red@0.9:t=6,scale=270:-1",
                            str(png)], check=True)
            tiles.append(png)
        cols = min(6, len(tiles))
        rows_n = -(-len(tiles) // cols)
        inputs = sum((["-i", str(p)] for p in tiles), [])
        sheet = qa / "facezone-check.jpg"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex",
                        f"xstack=inputs={len(tiles)}:layout=" + "|".join(f"{(i % cols) * 270}_{(i // cols) * 480}" for i in range(len(tiles)))
                        + f":fill=black", str(sheet)], check=True)
        for p in tiles:
            p.unlink()
        add("抽格確認圖", "ok", f"{sheet.relative_to(proj)}（{rows_n} 列，紅框＝臉部安全區）")

    print("| 結果 | 項目 | 說明 |\n|---|---|---|")
    print("\n".join(rows))
    print("\n有失敗項目，修正後再交付。" if fail else "\n全部通過（⚠ 的項目請看抽格圖人工確認）。")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
