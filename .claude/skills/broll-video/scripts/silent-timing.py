#!/usr/bin/env python3
"""無聲模式：沒有配音時，用「閱讀速度」幫逐字稿排時間，產生和 transcribe.py 一模一樣的時間檔。

原理：依字數算出每個字的出現時間，寫成假的辨識結果（asr_raw.json），
再交給 transcribe.py --reuse 產生 words.json、lines.json、transcript.srt、alignment.md。
所以後面的分鏡、prepare-composition、渲染流程完全不用改。

同時產生一段同長度的靜音音檔（inputs/silent.m4a），給 Hyperframes 的 --audio 用；
之後要加背景音樂或換成真人配音，照 SKILL.md 的說明替換即可。

用法：
  python3 silent-timing.py projects/<名稱>/inputs/transcript.txt --out projects/<名稱>/storyboard/timing \
      [--cps 4.5] [--gap 0.4] [--lead 0.6] [--tail 1.5]

閱讀速度 --cps（每秒幾個字）：用看的比用聽的慢。
  4.5 預設；字幕很短、畫面很簡單可以到 5；資訊密度高、有數字和專有名詞時用 4。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COUNT = re.compile(r"[A-Za-z]+|[0-9]|[㐀-鿿豈-﫿]")
MIN_LINE = 1.5   # 每句最少停留秒數（太短的句子看不完）


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript", help="逐字稿 txt（一行一句）")
    ap.add_argument("--out", required=True, help="時間檔輸出資料夾（通常是 storyboard/timing）")
    ap.add_argument("--cps", type=float, default=4.5, help="閱讀速度：每秒幾個字（預設 4.5）")
    ap.add_argument("--gap", type=float, default=0.4, help="句子之間的空白秒數（預設 0.4）")
    ap.add_argument("--lead", type=float, default=0.6, help="開頭空白秒數（預設 0.6）")
    ap.add_argument("--tail", type=float, default=1.5, help="最後一句後多留幾秒（預設 1.5）")
    ap.add_argument("--audio-out", help="靜音音檔路徑（預設：逐字稿同資料夾的 silent.m4a）")
    a = ap.parse_args()

    tpath = Path(a.transcript)
    lines = [re.sub(r"\s+", " ", l.strip()) for l in tpath.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        sys.exit("逐字稿是空的")

    t = a.lead
    segments, table = [], []
    for li, line in enumerate(lines, 1):
        units = COUNT.findall(line)
        if not units:
            continue
        dur = max(MIN_LINE, len(units) / a.cps)
        per = dur / len(units)
        words = [{"text": u, "start": round(t + i * per, 3), "end": round(t + (i + 1) * per, 3), "prob": 1.0}
                 for i, u in enumerate(units)]
        segments.append({"start": round(t, 3), "end": round(t + dur, 3), "text": line, "words": words})
        table.append((li, t, t + dur, line))
        t += dur + a.gap
    total = round(t - a.gap + a.tail, 2)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    asr = {"language": "zh", "duration": total, "segments": segments, "silent": True,
           "note": f"無聲模式：依閱讀速度 {a.cps} 字/秒排出的時間，不是語音辨識結果"}
    (out / "asr_raw.json").write_text(json.dumps(asr, ensure_ascii=False, indent=1), encoding="utf-8")

    # 交給 transcribe.py 產生其餘時間檔（--reuse：不跑語音辨識，media 參數不會被讀取）
    r = subprocess.run([sys.executable, str(HERE / "transcribe.py"), "silent", "--transcript", str(tpath),
                        "--out", str(out), "--reuse"])
    if r.returncode != 0:
        sys.exit("transcribe.py --reuse 失敗")
    rep = out / "alignment.md"
    rep.write_text("> **無聲模式**：時間是依閱讀速度排的（%s 字/秒），沒有配音。換成真人或 AI 配音後，請重跑 transcribe.py。\n\n"
                   % a.cps + rep.read_text(encoding="utf-8"), encoding="utf-8")

    audio = Path(a.audio_out) if a.audio_out else tpath.parent / "silent.m4a"
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-t", str(total), "-c:a", "aac", "-b:a", "64k", str(audio)], check=True)
        print(f"靜音音檔：{audio}（{total} 秒）")
    except Exception as e:
        print(f"!! 靜音音檔產生失敗（{e}）；請確認有安裝 ffmpeg", file=sys.stderr)

    print(f"\n無聲模式時間表（閱讀速度 {a.cps} 字/秒）· 總長 {total} 秒")
    for li, s, e, line in table:
        print(f"{li:>2}  {s:6.2f}–{e:6.2f}  {line}")


if __name__ == "__main__":
    main()
