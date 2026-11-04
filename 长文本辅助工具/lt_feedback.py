#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lt_feedback.py —— 接收用户反馈，喂回三条回路。

用法：
  python lt_feedback.py add 反馈.json          # 记一条反馈
  python lt_feedback.py stats                  # 看骨架胜率与判据偏差
  python lt_feedback.py report rpt-xxx         # 看某次报告的反馈汇总

反馈 json 结构见 反馈接口.md。最小可用：
{
  "report_id": "rpt-20261105-0001",
  "verdict": "partial",
  "taunt_reaction": "stung",
  "skeleton": "骨 3",
  "disputes": [{"section":"logic","item":"小伙伴消失","tool_score":7.5,"user_score":9.0}]
}
"""
import json
import os
import sys
import datetime
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.join(BASE, "反馈表.jsonl")

VALID_VERDICT = ("agree", "partial", "disagree")
VALID_REACT = ("broken", "stung", "flat", "wrong")

# 骨架胜率权重
REACT_W = {"broken": 1.0, "stung": 0.3, "flat": 0.0, "wrong": -1.0}


def load():
    if not os.path.exists(FB):
        return []
    return [json.loads(l) for l in open(FB, encoding="utf-8") if l.strip()]


def save(rows):
    with open(FB, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_add(path):
    e = json.load(open(path, encoding="utf-8"))
    errs = []
    if not e.get("report_id"):
        errs.append("缺 report_id")
    if e.get("verdict") not in VALID_VERDICT:
        errs.append("verdict 必须是 %s" % "/".join(VALID_VERDICT))
    if e.get("taunt_reaction") not in VALID_REACT:
        errs.append("taunt_reaction 必须是 %s" % "/".join(VALID_REACT))
    if errs:
        print("✗ 拒绝：")
        for x in errs:
            print("   ·", x)
        return 1

    rows = load()
    e["feedback_id"] = "fb-%04d" % (len(rows) + 1)
    e.setdefault("submitted_at", datetime.datetime.now().isoformat(timespec="seconds"))
    e.setdefault("disputes", [])
    rows.append(e)
    save(rows)

    print("✓ 已记 fb-%s" % e["feedback_id"][3:])
    if e["taunt_reaction"] == "wrong":
        print("  ⚠ taunt_reaction=wrong → 该条骨架应立刻下架，先问清哪里错了")
    if e["verdict"] == "disagree":
        print("  ⚠ 完全不服 → 该篇标记待复核（不改分）")
    return 0


def cmd_stats():
    rows = load()
    if not rows:
        print("还没有反馈。")
        return 0

    print("=" * 58)
    print("总览：%d 条反馈" % len(rows))
    print("=" * 58)

    v = defaultdict(int)
    r = defaultdict(int)
    for x in rows:
        v[x["verdict"]] += 1
        r[x["taunt_reaction"]] += 1
    print("  分数态度:", dict(v))
    print("  嘲讽反应:", dict(r))

    print("\n" + "=" * 58)
    print("回路一 · 骨架胜率")
    print("=" * 58)
    sk = defaultdict(lambda: {"n": 0, "w": 0.0, "wrong": 0})
    for x in rows:
        s = x.get("skeleton")
        if not s:
            continue
        sk[s]["n"] += 1
        sk[s]["w"] += REACT_W.get(x["taunt_reaction"], 0.0)
        if x["taunt_reaction"] == "wrong":
            sk[s]["wrong"] += 1
    if not sk:
        print("  （反馈里没标 skeleton，无法统计）")
    for s, d in sorted(sk.items(), key=lambda kv: kv[1]["w"] / max(kv[1]["n"], 1)):
        rate = d["w"] / d["n"]
        tag = ""
        if d["wrong"]:
            tag = "  ← 有事实错误，应下架"
        elif d["n"] >= 3 and rate < 0.2:
            tag = "  ← 胜率过低，标记 suspect"
        elif rate >= 0.6:
            tag = "  ← 好用"
        print("  %-8s 用 %d 次  胜率 %+.2f%s" % (s, d["n"], rate, tag))

    print("\n" + "=" * 58)
    print("回路二 · 判据偏差（连续同向才改）")
    print("=" * 58)
    dev = defaultdict(list)
    for x in rows:
        for d in x.get("disputes") or []:
            delta = (d.get("user_score") or 0) - (d.get("tool_score") or 0)
            dev[(d.get("section"), d.get("item"))].append(delta)
    if not dev:
        print("  （暂无分项争议）")
    for (sec, item), ds in dev.items():
        same = all(d > 0 for d in ds) or all(d < 0 for d in ds)
        flag = ""
        if len(ds) >= 3 and same:
            flag = "  ← 连续 %d 次同向，建议校准判据" % len(ds)
        print("  %s / %s  争议 %d 次  平均偏差 %+.2f%s"
              % (sec, item, len(ds), sum(ds) / len(ds), flag))
    return 0


def cmd_report(rid):
    rows = [x for x in load() if x.get("report_id") == rid]
    if not rows:
        print("没找到 %s 的反馈" % rid)
        return 0
    print("=" * 58)
    print("%s 的反馈（%d 条）" % (rid, len(rows)))
    print("=" * 58)
    for x in rows:
        print("  %s  verdict=%s  reaction=%s"
              % (x["feedback_id"], x["verdict"], x["taunt_reaction"]))
        for d in x.get("disputes") or []:
            print("     争议：%s/%s  工具 %s → 你认为 %s"
                  % (d.get("section"), d.get("item"),
                     d.get("tool_score"), d.get("user_score")))
        if x.get("quoted_dispute"):
            print("     不认的那句：%s" % x["quoted_dispute"])
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    c = sys.argv[1]
    if c == "add" and len(sys.argv) > 2:
        return cmd_add(sys.argv[2])
    if c == "stats":
        return cmd_stats()
    if c == "report" and len(sys.argv) > 2:
        return cmd_report(sys.argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
