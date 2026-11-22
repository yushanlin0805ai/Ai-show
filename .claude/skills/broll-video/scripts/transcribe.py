#!/usr/bin/env python3
"""語音轉文字＋逐字時間點對齊。

用 faster-whisper 產生字級時間點，再把時間對齊回「使用者提供的逐字稿原文」，
所以字幕用字以逐字稿為準，不會被辨識錯字取代。

用法：
  python3 transcribe.py <音檔或影片> --transcript transcript.txt --out <輸出資料夾> [--terms 阿斯巴甜,零卡可樂]
  python3 transcribe.py <音檔或影片> --out <輸出資料夾>        # 沒有逐字稿時，直接輸出辨識結果

輸出（都在 --out 裡）：
  asr_raw.json     faster-whisper 原始辨識結果（含字級時間）
  words.json       逐字時間點：[{"text","start","end","line"}]，中文以「字」為單位
  lines.json       逐句時間點：[{"line","text","start","end"}]（逐字稿的每一行／每一句）
  transcript.srt   字幕檔（每句一則，過長會在逗號處拆開）
  alignment.md     辨識結果與逐字稿不一致的地方（給人工檢查用）
"""
import argparse
import difflib
import json
import os
import re
import sys

# 關閉 Hugging Face 的 xet 傳輸，改走一般 HTTPS 下載（公司／雲端網路較容易放行）
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from pathlib import Path

PUNCT = set("，。、！？：；「」『』（）《》〈〉…—～·,.!?:;\"'()[]{}<>-~ 　\t\n")
# 每則字幕最多幾個字寬：9:16 畫面、字幕 69px，一行約放 13 字；一則只用一行，避免在詞中間換行
MAX_CUE_CHARS = 13
UNIT_RE = r"[A-Za-z]+|."


def fmt_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_trad(text):
    """若有安裝 opencc，把簡體辨識結果轉繁體再比對（沒有也能跑，只是比對率較低）。"""
    try:
        import opencc  # type: ignore
        return opencc.OpenCC("s2twp").convert(text)
    except Exception:
        return text


def load_audio(media, sr=16000):
    """用 ffmpeg 把任何音檔／影片轉成 16kHz 單聲道（避開 PyAV 版本相容問題）。"""
    import subprocess
    import numpy as np
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(media),
           "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def run_asr(media, model_name, language, prompt, device, hotwords=None):
    from faster_whisper import WhisperModel
    compute = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_name, device=device, compute_type=compute)
    segments, info = model.transcribe(
        load_audio(media),
        language=language,
        word_timestamps=True,
        initial_prompt=prompt,
        hotwords=hotwords,
        vad_filter=True,
        beam_size=5,
    )
    out = {"language": info.language, "duration": info.duration, "segments": []}
    for seg in segments:
        out["segments"].append({
            "start": seg.start, "end": seg.end, "text": seg.text,
            "words": [{"text": w.word, "start": w.start, "end": w.end, "prob": w.probability}
                      for w in (seg.words or [])],
        })
        print(f"  [{seg.start:6.2f}-{seg.end:6.2f}] {seg.text.strip()}", file=sys.stderr)
    return out


def asr_chars(asr):
    """把辨識出的詞拆成「字」，每個字平均分配該詞的時間。"""
    chars = []
    for seg in asr["segments"]:
        for w in seg["words"]:
            text = to_trad(w["text"].strip())
            body = [c for c in text if c not in PUNCT]
            if not body:
                continue
            # 英文字（如 WHO）視為一個單位；數字逐位比對（2023 → 2,0,2,3）
            units = re.findall(UNIT_RE, "".join(body))
            n = len(units)
            dur = (w["end"] - w["start"]) / n
            for i, u in enumerate(units):
                chars.append({"text": u, "start": w["start"] + i * dur, "end": w["start"] + (i + 1) * dur})
    return chars


def transcript_units(lines):
    """逐字稿 → 字單位（去掉標點），記錄屬於第幾行。"""
    units = []
    for li, line in enumerate(lines):
        for u in re.findall(UNIT_RE, line):
            if u in PUNCT or u.strip() == "":
                continue
            units.append({"text": u, "line": li})
    return units


def align(units, chars):
    a = [u["text"] for u in units]
    b = [c["text"] for c in chars]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    times = [None] * len(units)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (chars[j1 + k]["start"], chars[j1 + k]["end"])
        elif tag == "replace" and j2 > j1:
            # 用辨識端的時間範圍平均分給逐字稿這幾個字
            s, e = chars[j1]["start"], chars[j2 - 1]["end"]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (s + (e - s) * k / n, s + (e - s) * (k + 1) / n)
            diffs.append(("不同", "".join(a[i1:i2]), "".join(b[j1:j2]), s))
        elif tag == "delete":
            diffs.append(("辨識沒聽到", "".join(a[i1:i2]), "", chars[j1 - 1]["end"] if j1 else 0.0))
        elif tag == "insert":
            diffs.append(("逐字稿沒有", "", "".join(b[j1:j2]), chars[j1]["start"]))
    # 補齊沒對到的字：在前後已知時間之間線性內插
    known = [i for i, t in enumerate(times) if t]
    if not known:
        raise SystemExit("對齊失敗：逐字稿和辨識結果幾乎沒有相同的字，請確認檔案是否對應。")
    for i in range(len(times)):
        if times[i]:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        if prev is None:
            times[i] = (times[nxt][0], times[nxt][0])
        elif nxt is None:
            times[i] = (times[prev][1], times[prev][1])
        else:
            s, e = times[prev][1], times[nxt][0]
            span = nxt - prev
            times[i] = (s + (e - s) * (i - prev - 1) / span, s + (e - s) * (i - prev) / span)
    for u, t in zip(units, times):
        u["start"], u["end"] = round(t[0], 3), round(t[1], 3)
    return units, diffs, sm.ratio()


def word_bounds(text):
    """用 Node 內建的 Intl.Segmenter 找中文詞的邊界（不需另外安裝斷詞套件）。
    回傳可以斷開的字元位置集合；沒有 Node 時回傳 None（改用簡單規則）。"""
    import subprocess
    js = ('const t=process.argv[1];const s=new Intl.Segmenter("zh-Hant",{granularity:"word"});'
          'let i=0,o=[];for(const x of s.segment(t)){i+=x.segment.length;o.push(i)}console.log(JSON.stringify(o))')
    try:
        out = subprocess.run(["node", "-e", js, text], capture_output=True, text=True, check=True).stdout
        return set(json.loads(out))
    except Exception:
        return None


def split_cue(text, terms=()):
    """把一句拆成一行一則的字幕：先在逗號處拆，太長再在詞與詞之間拆。"""
    if cue_width(text) <= MAX_CUE_CHARS:
        return [text]
    parts = re.split(r"(?<=[，、；：,])", text)
    cues, cur = [], ""
    for p in parts:
        if cur and cue_width(cur + p) > MAX_CUE_CHARS:
            cues.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        cues.append(cur)
    # 只有一兩個字的片段（如「因此，」）併到下一段，避免字幕一閃而過；允許超出 1 字，畫面會自動縮字
    merged, roomy = [], set()
    for c in cues:
        if merged and cue_width(merged[-1]) <= 2 and cue_width(merged[-1] + c) <= MAX_CUE_CHARS + 2:
            merged[-1] += c
            roomy.add(len(merged) - 1)
        else:
            merged.append(c)
    # 不可拆開的範圍：「」裡的詞、專有名詞（--terms 與逐字稿中「」的詞）
    def protected(c):
        bad = set()
        for m in re.finditer(r"「[^」]*」", c):
            bad.update(range(m.start() + 1, m.end()))
        for t in terms:
            for m in re.finditer(re.escape(t), c):
                bad.update(range(m.start() + 1, m.end()))
        return bad
    out = []
    for idx, c in enumerate(merged):
        c = c.strip()
        while cue_width(c) > MAX_CUE_CHARS + (2 if idx in roomy else 0):
            n = -(-cue_width(c) // MAX_CUE_CHARS)
            target = cue_width(c) / n
            bounds = word_bounds(c)
            bad = protected(c)
            best, best_score = None, None
            for i in range(2, len(c) - 1):
                left, right = c[:i], c[i:]
                if cue_width(left) < 2 or cue_width(right) < 2 or cue_width(left) > MAX_CUE_CHARS:
                    continue
                if c[i - 1].isascii() and c[i - 1].isalnum() and c[i].isascii() and c[i].isalnum():
                    continue  # 不切在數字或英文字中間
                if i in bad:
                    continue  # 不拆開專有名詞
                if bounds is not None and i not in bounds:
                    continue  # 不切在詞中間
                if c[i] in "」』）》，。！？、" or c[i - 1] in "「『（《":
                    continue  # 不讓引號、標點落單
                # 「的」之後斷開較自然，但「的人」「的事」這種後面只接一個字的不算
                nxt = min((b for b in (bounds or ()) if b > i), default=len(c))
                after_de = c[i - 1] == "的" and (bounds is None or nxt - i >= 2)
                preferred = after_de or any(c.startswith(w, i) for w in BREAK_BEFORE)
                score = abs(cue_width(left) - target) - (2.5 if preferred else 0)
                if best_score is None or score < best_score:
                    best, best_score = i, score
            if best is None:
                best = next(i for i in range(1, len(c)) if cue_width(c[:i]) >= target)
            out.append(c[:best].strip())
            c = c[best:].strip()
        out.append(c)
    return out


BREAK_BEFORE = ["或", "還", "就", "才", "但", "而", "並", "跟", "和", "與", "也", "都",
                "大約", "大概", "可能", "不是", "所以", "因為", "因此", "如果"]


def cue_width(text):
    """字幕顯示寬度：中文 1、英數與空白 0.5。結尾的逗號、句號不顯示所以不算；「？」「！」會顯示，要算。"""
    text = text.rstrip("，、；：,。. ")
    return sum(0.5 if ch.isascii() else 1 for ch in text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media")
    ap.add_argument("--transcript", help="逐字稿 txt（一行一句）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="large-v3", help="faster-whisper 模型（預設 large-v3；電腦慢可用 medium）")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--device", default="auto", help="cpu / cuda / auto")
    ap.add_argument("--terms", help="額外專有名詞，逗號分隔（例：阿斯巴甜,IARC,零卡可樂）")
    ap.add_argument("--reuse", action="store_true", help="已有 asr_raw.json 時直接沿用，不重跑辨識")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    if args.transcript:
        lines = [re.sub(r"\s+", " ", l.strip()) for l in Path(args.transcript).read_text(encoding="utf-8").splitlines() if l.strip()]

    # 專有名詞：逐字稿中「」括起來的詞＋ --terms。辨識時當 hotwords，切字幕時不拆開
    terms = [t.strip() for t in re.findall(r"「([^」]{1,12})」", "\n".join(lines))
             + (args.terms.split(",") if args.terms else []) if t.strip()]
    raw_path = out / "asr_raw.json"
    if args.reuse and raw_path.exists():
        asr = json.loads(raw_path.read_text(encoding="utf-8"))
    else:
        device = args.device
        if device == "auto":
            try:
                import ctranslate2
                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"
        # 不把整份逐字稿當 prompt（模型會以為那些話已經講過而跳過開頭），
        # 只把專有名詞當 hotwords：逐字稿中「」括起來的詞＋ --terms
        hotwords = " ".join(dict.fromkeys(t.strip() for t in terms if t.strip())) or None
        prompt = "以下是繁體中文的衛教口播。"
        print(f"辨識中：{args.media}（模型 {args.model}，{device}，關鍵詞：{hotwords}）", file=sys.stderr)
        asr = run_asr(args.media, args.model, args.language, prompt, device, hotwords)
        raw_path.write_text(json.dumps(asr, ensure_ascii=False, indent=1), encoding="utf-8")

    chars = asr_chars(asr)
    if not lines:
        # 沒有逐字稿：以辨識段落當句子
        lines = [to_trad(s["text"].strip()) for s in asr["segments"]]
    units, diffs, ratio = align(transcript_units(lines), chars)

    line_objs = []
    for li, text in enumerate(lines):
        us = [u for u in units if u["line"] == li]
        if not us:
            continue
        line_objs.append({"line": li + 1, "text": text, "start": us[0]["start"], "end": us[-1]["end"]})

    (out / "words.json").write_text(json.dumps(
        [{"text": u["text"], "start": u["start"], "end": u["end"], "line": u["line"] + 1} for u in units],
        ensure_ascii=False, indent=0), encoding="utf-8")
    (out / "lines.json").write_text(json.dumps(line_objs, ensure_ascii=False, indent=1), encoding="utf-8")

    # SRT：長句依逗號拆開，時間按字數比例分配
    srt, n = [], 1
    for lo in line_objs:
        us = [u for u in units if u["line"] == lo["line"] - 1]
        idx = 0
        for cue in split_cue(lo["text"], terms):
            k = len([c for c in re.findall(UNIT_RE, cue) if c not in PUNCT and c.strip()])
            seg = us[idx: idx + k] or us[-1:]
            idx += k
            srt.append(f"{n}\n{fmt_srt(seg[0]['start'])} --> {fmt_srt(seg[-1]['end'])}\n{cue.rstrip('，、；：,。.')}\n")
            n += 1
    (out / "transcript.srt").write_text("\n".join(srt), encoding="utf-8")

    rep = [f"# 對齊報告\n", f"- 逐字稿與辨識結果相似度：{ratio:.0%}",
           f"- 音檔長度：{asr['duration']:.2f} 秒", f"- 逐字稿句數：{len(line_objs)}\n",
           "以下是辨識結果與逐字稿不同的地方。多數是數字寫法（2023 vs 二零二三）或同音字，",
           "時間點已自動內插；若某句差異很大，代表口播可能和逐字稿不一樣，請人工確認。\n",
           "| 約略秒數 | 類型 | 逐字稿 | 辨識結果 |", "|---|---|---|---|"]
    for kind, t_txt, a_txt, t in diffs:
        rep.append(f"| {t:.1f} | {kind} | {t_txt} | {a_txt} |")
    (out / "alignment.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"完成：相似度 {ratio:.0%}，{len(line_objs)} 句，輸出在 {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
