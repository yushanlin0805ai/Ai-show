#!/usr/bin/env python3
"""用 Fish Audio 把口播腳本轉成配音（取代自己錄音，之後走模式 A）。

用法：
  python3 fish-tts.py <script.txt> <輸出.mp3> --voice <聲音 ID> [--speed 1.0] [--free] [--dry-run]

金鑰（二擇一）：
  建議：Claude Code 環境的「Network secrets」加一個 secret，Allowed websites＝api.fish.audio，
        Header＝Authorization、Prefix＝Bearer、Value＝金鑰。代理會自動幫請求加上金鑰，工作階段看不到金鑰，也不用改網路設定。
  備用：環境變數 FISH_API_KEY（環境的使用者都看得到，且要另外允許 api.fish.audio 連線）。
  金鑰絕對不要寫進任何檔案或 commit。
聲音 ID：在 fish.audio 複製自己的聲音後，聲音頁面網址最後那串，記在 brands/<品牌>/voice.md。

API：POST https://api.fish.audio/v1/tts（docs.fish.audio/features/text-to-speech）。只用標準函式庫，不用安裝套件。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.fish.audio/v1/tts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script", help="口播腳本，一行一句")
    ap.add_argument("out", help="輸出音檔（.mp3 或 .wav）")
    ap.add_argument("--voice", required=True, help="Fish Audio 聲音 ID（reference_id）")
    ap.add_argument("--speed", type=float, default=1.0, help="語速 0.5～2.0，預設 1.0")
    ap.add_argument("--free", action="store_true", help="用免費測試模型 s2.1-pro-free（沒有品質保證，正式影片別用）")
    ap.add_argument("--dry-run", action="store_true", help="只印出要送的內容，不呼叫 API")
    a = ap.parse_args()

    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip()]
    if not lines:
        sys.exit("腳本是空的")
    if not 0.5 <= a.speed <= 2.0:
        sys.exit("--speed 要在 0.5～2.0 之間")

    fmt = "wav" if a.out.lower().endswith(".wav") else "mp3"
    body = {
        "text": "\n".join(lines),
        "reference_id": a.voice,
        "format": fmt,
        "language": "zh-TW",          # 數字、單位照台灣習慣唸；不影響口音
        "normalize": True,
        "prosody": {"speed": a.speed},
    }
    if fmt == "mp3":
        body["mp3_bitrate"] = 192
    else:
        body["sample_rate"] = 44100
    model = "s2.1-pro-free" if a.free else "s2.1-pro"

    if a.dry_run:
        print(f"model: {model}")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return

    headers = {"Content-Type": "application/json", "model": model}
    key = os.environ.get("FISH_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    # 沒有 FISH_API_KEY 時不帶金鑰：由 Claude Code 的 Network secret 在代理端自動加上

    req = urllib.request.Request(API, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            audio = r.read()
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:500]
        hints = {
            401: "沒有收到有效的金鑰：確認環境的 Network secrets 有 api.fish.audio 那一筆（或 FISH_API_KEY 正確）",
            402: "帳戶 API 額度不足：到 fish.audio 的 API 頁面儲值，或先加 --free 測試",
            400: "聲音 ID 或參數有誤，確認 --voice 是不是自己的聲音 ID",
            429: "同時太多請求，等一下再試",
        }
        sys.exit(f"Fish Audio 回傳 {e.code}：{hints.get(e.code, '')}\n{msg}")
    except urllib.error.URLError as e:
        sys.exit(f"連不到 api.fish.audio（{e.reason}）。請在環境的 Network secrets 加上 api.fish.audio 的金鑰（會自動放行），或在網路設定允許這個網域。")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(audio)
    print(f"已輸出 {a.out}（{len(audio) / 1024:.0f} KB，模型 {model}）")


if __name__ == "__main__":
    main()
