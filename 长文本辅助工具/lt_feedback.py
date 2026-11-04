#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lt_feedback.py —— 反馈的接收端。

用户侧只填四个空（见 反馈模板.txt），交给这里：

  python lt_feedback.py intake 用户填好的.txt

同时写两个地方：
  反馈记录.txt    按时间顺序，人能直接读，只追加
  反馈表.jsonl    结构化，用来算骨架胜率

其他命令：
  python lt_feedback.py stats     看骨架胜率
  python lt_feedback.py tail 10   看最近 10 条
"""
import json
import os
import sys
import re
import datetime
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(BASE, "反馈表.jsonl")
TXT = os.path.join(BASE, "反馈记录.txt")

# 嘲讽够不够力
FORCE_MAP = {
    "不够": "weak", "太轻": "weak", "没感觉": "weak", "挠痒痒": "weak",
    "刚好": "right", "合适": "right", "正好": "right",
    "过了": "over", "太狠": "over", "过头": "over", "伤人": "over",
}
FORCE_CN = {"weak": "不够", "right": "刚好", "over": "过了"}

# 骨架胜率权重（2026-11-05 作者定稿）
# 「过了」不是越界，是**目标**——往死里嘲讽本来就该把人惹毛。
# 不够 -> 0（白写了）；刚好 -> +0.2（有效但还留了面子）；过了 -> +1.0（成功）
FORCE_W = {"weak": 0.0, "right": 0.2, "over": 1.0}


def load():
    if not os.path.exists(JSONL):
        return []
    return [json.loads(l) for l in open(JSONL, encoding="utf-8") if l.strip()]


def save(rows):
    with open(JSONL, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def parse_kv(path):
    out = {}
    for line in open(path, encoding="utf-8-sig"):
        m = re.match(r"^([^:：]+)[:：]\s*(.*)$", line.strip())
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def cmd_intake(path):
    kv = parse_kv(path)

    raw = kv.get("嘲讽够不够力", "")
    force = FORCE_MAP.get(raw, "")
    if not force:
        print("✗ 「嘲讽够不够力」只认：不够 / 刚好 / 过了（你填的是「%s」）" % raw)
        return 1

    rows = load()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    e = {
        "feedback_id": "fb-%04d" % (len(rows) + 1),
        "submitted_at": now,
        "force": force,
        "no_face": kv.get("哪里面子没给够", ""),
        "free_comment": kv.get("想说的话", ""),
    }
    rows.append(e)
    save(rows)

    new = not os.path.exists(TXT)
    with open(TXT, "a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("反馈记录（按时间顺序，只追加）\n")
            f.write("=" * 56 + "\n\n")
        f.write("[%s]  %s\n" % (now[:19].replace("T", " "), e["feedback_id"]))
        f.write("  嘲讽够不够力：%s\n" % FORCE_CN[force])
        if e["no_face"]:
            f.write("  哪里面子没给够：%s\n" % e["no_face"])
        if e["free_comment"]:
            f.write("  想说的：%s\n" % e["free_comment"])
        f.write("\n")

    print("✓ 已记 %s" % e["feedback_id"])
    print("  反馈记录.txt（按时间顺序）  +  反馈表.jsonl（结构化）")
    if force == "over":
        print("  ✓ 标了「过了」—— 这条骨架记满分，说明真扎到了")
    if force == "weak":
        print("  ⚠ 标了「不够」—— 这条骨架该加重或淘汰")
    return 0


def cmd_stats():
    rows = load()
    if not rows:
        print("还没有反馈。")
        return 0
    print("=" * 56)
    print("总览：%d 条反馈" % len(rows))
    print("=" * 56)
    c = defaultdict(int)
    for x in rows:
        c[x["force"]] += 1
    print("  嘲讽力度：", {FORCE_CN[k]: n for k, n in c.items()})
    n = len(rows)
    over = c.get("over", 0) / n
    weak = c.get("weak", 0) / n
    print("  「过了」占比 %.0f%%   ← 这是目标，越高越好" % (over * 100))
    if weak >= 0.5:
        print("  ⚠ 「不够」占 %.0f%% —— 力度明显不足，骨架要换" % (weak * 100))
    elif over >= 0.5:
        print("  ✓ 「过了」占 %.0f%% —— 力度到位" % (over * 100))
    else:
        print("  · 力度偏温和，还能再狠一点")

    face = [x for x in rows if x.get("no_face")]
    if face:
        print("\n  被提到的「面子没给够」的地方：")
        for x in face[:10]:
            print("   · %s" % x["no_face"])

    print("\n" + "=" * 56)
    print("骨架胜率")
    print("=" * 56)
    sk = defaultdict(lambda: {"n": 0, "w": 0.0})
    for x in rows:
        s = x.get("skeleton")
        if not s:
            continue
        sk[s]["n"] += 1
        sk[s]["w"] += FORCE_W.get(x["force"], 0.0)
    if not sk:
        print("  （反馈里没标 skeleton；等接口化之后自动带上）")
    for s, d in sorted(sk.items(), key=lambda kv: kv[1]["w"] / max(kv[1]["n"], 1)):
        rate = d["w"] / d["n"]
        tag = "  ← 好用" if rate >= 0.6 else ("  ← 该淘汰" if d["n"] >= 3 and rate < 0.2 else "")
        print("  %-8s 用 %d 次  胜率 %+.2f%s" % (s, d["n"], rate, tag))
    return 0


def cmd_tail(n):
    rows = load()
    if not rows:
        print("还没有反馈。")
        return 0
    for x in rows[-int(n):]:
        print("[%s] %s  力度=%s" % (x["submitted_at"][:19].replace("T", " "),
                                    x["feedback_id"], FORCE_CN[x["force"]]))
        for k, lab in (("no_face", "面子"), ("quoted_dispute", "反驳"), ("free_comment", "想说")):
            if x.get(k):
                print("   %s：%s" % (lab, x[k]))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    c = sys.argv[1]
    if c == "intake" and len(sys.argv) > 2:
        return cmd_intake(sys.argv[2])
    if c == "stats":
        return cmd_stats()
    if c == "tail":
        return cmd_tail(sys.argv[2] if len(sys.argv) > 2 else 10)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
