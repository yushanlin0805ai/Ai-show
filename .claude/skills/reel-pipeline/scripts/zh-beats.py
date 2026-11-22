#!/usr/bin/env python3
"""中文口播腳本的時間估算與檢查（ig-reel 的 beats.py／hookscore.py 只認得英文，中文會算成 0 字）。

用法：
  python3 zh-beats.py <腳本.txt> [--cps 5.5] [--target 60] [--keyword 測驗] [--extra "一覺到天亮|快速瘦"]

腳本格式：一行一句（和 inputs/transcript.txt 相同），空行會略過。
語速 cps＝每秒幾個字（中文字＋英數字）。實測：
  沉穩講解型 約 5.5 字／秒；親切聊天型 約 7.5～8 字／秒
  自己的語速：錄一支後請 Claude 算（字數 ÷ 秒數），寫進 brands/<品牌>/voice.md
"""
import argparse
import re
import sys

BANNED = r"治療|治癒|根治|療效|藥效|保證|絕對|100%|排毒|神奇|奇蹟|抗癌"  # 產業禁用詞用 --extra 加
COUNT = re.compile(r"[㐀-鿿豈-﫿A-Za-z0-9]")
NUMBER = re.compile(r"[0-9０-９]|[一二三四五六七八九十百千萬兩]+(?:個|種|類|天|週|周|年|公斤|毫克|罐|杯|次|倍|成|分鐘|秒)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--cps", type=float, default=5.5, help="語速：每秒字數")
    ap.add_argument("--target", type=float, default=0, help="目標秒數（可選）")
    ap.add_argument("--keyword", default="", help="CTA 留言關鍵字（可選）")
    ap.add_argument("--extra", default="", help="產業禁用詞，用 | 分隔（從 brands/<品牌>/compliance.md 複製）")
    a = ap.parse_args()

    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip()]
    if not lines:
        sys.exit("腳本是空的")

    t = 0.0
    flags = []
    print(f"BEAT SHEET（中文）· {len(lines)} 句 · 語速 {a.cps} 字／秒")
    print("=" * 64)
    for i, line in enumerate(lines, 1):
        n = len(COUNT.findall(line))
        d = n / a.cps + 0.2  # 句間停頓
        tag = "開場" if i == 1 else ("結尾" if i == len(lines) else "")
        print(f"{int(t // 60)}:{t % 60:04.1f}  {d:4.1f}s  {tag:4} {line}")
        if i == 1 and d > 4.0:
            flags.append(f"第 1 句（開場）約 {d:.1f} 秒，超過 4 秒，觀眾還沒聽到重點就滑走了，試著砍短")
        if i > 1 and d > 6.0:
            flags.append(f"第 {i} 句約 {d:.1f} 秒，太長，拆成兩句（畫面也比較好換）")
        t += d
    print("-" * 64)
    print(f"總長約 {t:.1f} 秒")

    if not NUMBER.search(lines[0]) and not re.search(r"[？?]", lines[0]):
        flags.append("開場沒有數字，也不是問句：觀眾沒有理由停下來")
    if a.target and abs(t - a.target) > a.target * 0.2:
        flags.append(f"和目標 {a.target:.0f} 秒差了 {t - a.target:+.0f} 秒")
    if a.keyword and not any(a.keyword in l for l in lines[-3:]):
        flags.append(f"最後三句沒有出現留言關鍵字「{a.keyword}」")
    asks = sum(1 for l in lines if re.search(r"留言|追蹤|收藏|分享|私訊|點連結", l))
    if asks > 1:
        flags.append(f"出現 {asks} 個行動呼籲（留言／追蹤／收藏…），結尾只留一個")
    for i, line in enumerate(lines, 1):
        for m in re.finditer(BANNED + ('|' + a.extra if a.extra else ''), line):
            flags.append(f"第 {i} 句有禁用詞「{m.group()}」（見 compliance.md）")

    if flags:
        print("\n需要處理：")
        for f in flags:
            print("  - " + f)
        print("\n結果：REVIEW")
    else:
        print("\n結果：PASS")


if __name__ == "__main__":
    main()
