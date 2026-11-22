#!/usr/bin/env python3
"""找出實拍影片裡講者的臉在哪，寫成「臉部安全區」（動畫不能放的範圍）。

用法：
  python3 face-zone.py <影片> --project projects/<名稱> [--fps 1] [--sheet storyboard/faces/face-zone.jpg]

做法：每秒抽一格（縮成 540 寬加速），用 OpenCV 內建的正臉偵測器（Haar cascade）找臉，
把所有偵測到的臉框取聯集，再往外加邊界（上方加大，包含頭髮；下方包含下巴），
寫進 project.json 的 "face_zone"：{"x0","y0","x1","y1","frames","detected"}（原片像素）。
同時產生一張抽格圖，紅框＝臉部安全區，給人工確認（含講者臉，不進 Git）。

需要：pip install "opencv-python-headless<5"（OpenCV 5 拿掉了這個偵測器）
找不到臉（側臉、戴口罩、太暗）時會提示改用人工抽格判讀。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCALE_W = 540
# 臉框往外加的邊界（臉框寬高的比例）。Haar 臉框已含額頭到下巴，只需替頭髮多留一點
PAD_X, PAD_TOP, PAD_BOTTOM = 0.08, 0.25, 0.05


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"]["duration"])


def frames(video, fps, w, h):
    import numpy as np
    sh = round(h * SCALE_W / w)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale={SCALE_W}:{sh}",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (SCALE_W * sh)
    return np.frombuffer(raw, dtype=np.uint8)[: n * SCALE_W * sh].reshape(n, sh, SCALE_W), SCALE_W / w


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--project", required=True)
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--sheet", default="storyboard/faces/face-zone.jpg")
    args = ap.parse_args()
    try:
        import cv2
    except ImportError:
        sys.exit('缺 OpenCV：pip install "opencv-python-headless<5"')

    proj = Path(args.project)
    w, h, dur = probe(args.video)
    imgs, k = frames(args.video, args.fps, w, h)
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes = []
    for g in imgs:
        found = det.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(SCALE_W // 8, SCALE_W // 8))
        if len(found):
            x, y, bw, bh = max(found, key=lambda b: b[2] * b[3])  # 只取最大的臉（講者）
            boxes.append((x / k, y / k, bw / k, bh / k))
    if not boxes:
        sys.exit("沒有偵測到正臉。請改用人工抽格：ffmpeg -i <影片> -vf \"fps=1/4,scale=270:-1,tile=8x2\" -frames:v 1 contact.png")

    # 去掉誤判（手、玩偶、海報）：只留中心靠近「典型臉位置」、大小接近典型大小的框
    import numpy as np
    arr = np.array(boxes)
    cx, cy = arr[:, 0] + arr[:, 2] / 2, arr[:, 1] + arr[:, 3] / 2
    mcx, mcy, mw = np.median(cx), np.median(cy), np.median(arr[:, 2])
    keep = (np.abs(cx - mcx) < mw * 0.8) & (np.abs(cy - mcy) < mw * 0.8) & (np.abs(arr[:, 2] - mw) < mw * 0.5)
    arr = arr[keep]
    # 用 5%／95% 百分位數取範圍（講者偶爾大動作不會把安全區撐爆）
    pct = lambda v, q: float(np.percentile(v, q))
    x0 = pct(arr[:, 0] - arr[:, 2] * PAD_X, 5)
    x1 = pct(arr[:, 0] + arr[:, 2] * (1 + PAD_X), 95)
    y0 = pct(arr[:, 1] - arr[:, 3] * PAD_TOP, 5)
    y1 = pct(arr[:, 1] + arr[:, 3] * (1 + PAD_BOTTOM), 95)
    zone = {"x0": max(0, int(x0)), "y0": max(0, int(y0)), "x1": min(w, int(x1)), "y1": min(h, int(y1)),
            "frames": len(imgs), "detected": int(keep.sum())}

    pj = proj / "project.json"
    cfg = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
    cfg["face_zone"] = zone
    pj.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sheet = proj / args.sheet
    sheet.parent.mkdir(parents=True, exist_ok=True)
    every = max(1, int(dur / 16))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(args.video), "-vf",
                    f"fps=1/{every},drawbox=x={zone['x0']}:y={zone['y0']}:w={zone['x1'] - zone['x0']}:h={zone['y1'] - zone['y0']}"
                    f":color=red@0.9:t=8,scale=270:-1,tile=8x2", "-frames:v", "1", str(sheet)], check=True)

    print(f"臉部安全區：x {zone['x0']}–{zone['x1']}、y {zone['y0']}–{zone['y1']}"
          f"（{zone['detected']}/{zone['frames']} 格偵測到臉）→ 已寫入 {pj}")
    print(f"抽格確認圖：{sheet}（紅框＝不能放動畫的範圍）")
    if zone["detected"] < zone["frames"] * 0.6:
        print("⚠ 不到六成的畫面偵測到臉（可能常轉頭或離開畫面），請一定要看抽格圖人工確認。")


if __name__ == "__main__":
    main()
