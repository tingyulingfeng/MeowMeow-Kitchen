#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lt_feedback.py —— 反馈的接收端。

用户侧只需填 反馈模板.txt 那五个空，交给这里：

  python lt_feedback.py intake 用户填好的.txt

会同时写两个地方：
  反馈记录.txt    按时间顺序，人能直接读
  反馈表.jsonl    结构化，用来算骨架胜率和判据偏差

其他命令：
  python lt_feedback.py stats            看骨架胜率与判据偏差
  python lt_feedback.py report <报告号>   看某次报告的全部反馈
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

# 用户填的中文 -> 内部值
VERDICT_MAP = {
    "服": "agree", "满意": "agree",
    "部分不服": "partial", "部分": "partial", "一半": "partial",
    "完全不服": "disagree", "不服": "disagree",
}
REACT_MAP = {
    "破防": "broken", "有感觉": "broken",
    "难受": "stung", "只是难受": "stung",
    "无感": "flat", "没感觉": "flat",
    "说错了": "wrong", "错了": "wrong",
}

REACT_W = {"broken": 1.0, "stung": 0.3, "flat": 0.0, "wrong": -1.0}
REACT_CN = {"broken": "破防", "stung": "难受", "flat": "无感", "wrong": "说错了"}
VERDICT_CN = {"agree": "服", "partial": "部分不服", "disagree": "完全不服"}


def load():
    if not os.path.exists(JSONL):
        return []
    return [json.loads(l) for l in open(JSONL, encoding="utf-8") if l.strip()]


def save(rows):
    with open(JSONL, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def parse_kv(path):
    """解析「键: 值」格式的文本"""
    out = {}
    for line in open(path, encoding="utf-8-sig"):
        m = re.match(r"^([^:：]+)[:：]\s*(.*)$", line.strip())
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def cmd_intake(path):
    kv = parse_kv(path)
    rid = kv.get("report_id", "").strip()
    if not rid:
        print("✗ 缺 report_id —— 报告末尾有一行「report_id: xxx」，抄过来")
        return 1

    verdict_raw = kv.get("服不服", "")
    react_raw = kv.get("嘲讽准不准", "")
    verdict = VERDICT_MAP.get(verdict_raw, "")
    react = REACT_MAP.get(react_raw, "")
    if not verdict:
        print("✗ 「服不服」只认：服 / 部分不服 / 完全不服（你填的是「%s」）" % verdict_raw)
        return 1
    if not react:
        print("✗ 「嘲讽准不准」只认：破防 / 只是难受 / 无感 / 说错了（你填的是「%s」）" % react_raw)
        return 1

    rows = load()
    e = {
        "feedback_id": "fb-%04d" % (len(rows) + 1),
        "report_id": rid,
        "submitted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "taunt_reaction": react,
        "dispute_raw": kv.get("哪项分不认", ""),
        "quoted_dispute": kv.get("想反驳的一句", ""),
        "free_comment": kv.get("想说的话", ""),
        "disputes": [],
    }
    rows.append(e)
    save(rows)

    # 追加到人能读的时间顺序文本
    new = not os.path.exists(TXT)
    with open(TXT, "a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("反馈记录（按时间顺序，只追加）\n")
            f.write("=" * 56 + "\n\n")
        f.write("[%s]  %s  ←  %s\n" % (e["submitted_at"][:19], e["feedback_id"], rid))
        f.write("  分数态度：%s\n" % VERDICT_CN[verdict])
        f.write("  嘲讽反应：%s\n" % REACT_CN[react])
        if e["dispute_raw"]:
            f.write("  不认的项：%s\n" % e["dispute_raw"])
        if e["quoted_dispute"]:
            f.write("  想反驳：%s\n" % e["quoted_dispute"])
        if e["free_comment"]:
            f.write("  想说的：%s\n" % e["free_comment"])
        f.write("\n")

    print("✓ 已记 %s" % e["feedback_id"])
    print("  写入：反馈记录.txt（按时间顺序）")
    print("       反馈表.jsonl（结构化）")
    if react == "wrong":
        print("  ⚠ 标了「说错了」—— 那条嘲讽要立刻下架，我该问你错在哪")
    if verdict == "disagree":
        print("  ⚠ 完全不服 —— 这篇标记待复核，但分数不直接改")
    return 0


def cmd_stats():
    rows = load()
    if not rows:
        print("还没有反馈。")
        return 0
    print("=" * 58)
    print("总览：%d 条反馈" % len(rows))
    print("=" * 58)
    v, r = defaultdict(int), defaultdict(int)
    for x in rows:
        v[x["verdict"]] += 1
        r[x["taunt_reaction"]] += 1
    print("  分数态度:", {VERDICT_CN[k]: n for k, n in v.items()})
    print("  嘲讽反应:", {REACT_CN[k]: n for k, n in r.items()})

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
        print("  （反馈里没标 skeleton，这一回路暂时空转）")
    for s, d in sorted(sk.items(), key=lambda kv: kv[1]["w"] / max(kv[1]["n"], 1)):
        rate = d["w"] / d["n"]
        tag = "  ← 有事实错误，应下架" if d["wrong"] else (
            "  ← 好用" if rate >= 0.6 else ("  ← 胜率过低" if d["n"] >= 3 and rate < 0.2 else ""))
        print("  %-8s 用 %d 次  胜率 %+.2f%s" % (s, d["n"], rate, tag))

    print("\n" + "=" * 58)
    print("回路二 · 判据偏差")
    print("=" * 58)
    dev = defaultdict(list)
    for x in rows:
        for d in x.get("disputes") or []:
            delta = (d.get("user_score") or 0) - (d.get("tool_score") or 0)
            dev[(d.get("section"), d.get("item"))].append(delta)
    if not dev:
        print("  （分项争议还没结构化，先记在文本里，攒够再统一录）")
        for x in rows:
            if x.get("dispute_raw"):
                print("   · %s：%s" % (x["feedback_id"], x["dispute_raw"]))
    else:
        for (sec, item), ds in dev.items():
            same = all(d > 0 for d in ds) or all(d < 0 for d in ds)
            flag = "  ← 连续 %d 次同向，建议校准" % len(ds) if len(ds) >= 3 and same else ""
            print("  %s / %s  争议 %d 次  平均偏差 %+.2f%s"
                  % (sec, item, len(ds), sum(ds) / len(ds), flag))
    return 0


def cmd_report(rid):
    rows = [x for x in load() if x.get("report_id") == rid]
    if not rows:
        print("没找到 %s 的反馈" % rid)
        return 0
    print("%s 的反馈（%d 条）" % (rid, len(rows)))
    for x in rows:
        print("  %s  %s / %s" % (x["feedback_id"], VERDICT_CN[x["verdict"]],
                                 REACT_CN[x["taunt_reaction"]]))
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
    if c == "report" and len(sys.argv) > 2:
        return cmd_report(sys.argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
