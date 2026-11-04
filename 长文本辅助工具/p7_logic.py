#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P7 逻辑（12 分）

判据（作者定）：**这个信息说不说，会不会改变读者的判断。**
会 → 逻辑问题；不会（只是可惜）→ 不是逻辑问题，可能是伏笔。

工具做两件事：
  ① 抽出可核对的硬信息，摆出来给人看
       · 时间轴：文中所有时间标记，按出现顺序排
       · 数字与量词：几百、七只、三间……
       · 指称：代词密度（"它/他/这/那"开头且无明确先行词）
  ② 读标注里的人工记录 `logic`，按严重度扣分

标注格式（在段落标注文件里加）
  "logic": [{"issue": "旧房子指代模糊", "severity": "中"}]
  severity: 重 / 中 / 轻

扣分：重 −3.0   中 −1.5   轻 −0.5

用法：python p7_logic.py 正文段落.jsonl [标注.jsonl]
"""
import json
import re
import sys

FULL = 12.0
PEN = {"重": 3.0, "中": 1.5, "轻": 0.5}

TIME_WORDS = ["小时候", "上幼儿园", "幼儿园毕业", "毕业后", "小学", "中学",
              "那年", "那天", "那时候", "后来", "从那以后", "几年后",
              "去年", "年底", "暑假", "寒假", "现在", "如今", "当时",
              "第二天", "第二天早上", "早上", "傍晚", "夜里"]

NUM_RE = re.compile(r"([一二三四五六七八九十百千万几数半两]+)\s*(只|个|间|座|条|口|窝|群|排|棵|片|层|岁|天|年|米)")


def timeline(paras):
    out = []
    for p in paras:
        for w in TIME_WORDS:
            for m in re.finditer(re.escape(w), p["text"]):
                out.append((p["para_id"], w, m.start()))
    # 同段内去重，保留首次出现
    seen, res = set(), []
    for pid, w, pos in sorted(out, key=lambda x: (x[0], x[2])):
        if (pid, w) in seen:
            continue
        seen.add((pid, w))
        res.append((pid, w))
    return res


def numbers(paras):
    out = []
    for p in paras:
        for m in NUM_RE.finditer(p["text"]):
            out.append((p["para_id"], m.group(0).strip()))
    return out


def pronouns(paras):
    """代词开头的句子（可能指代不明）"""
    out = []
    for p in paras:
        for s in re.split(r"[。！？…；]+", p["text"]):
            s = s.strip()
            if len(s) >= 4 and s[:1] in "它他她这那其":
                out.append((p["para_id"], s if len(s) <= 30 else s[:30] + "…"))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paras = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]

    tl = timeline(paras)
    nums = numbers(paras)
    prons = pronouns(paras)

    print("=" * 62)
    print("A. 时间轴（按出现顺序）")
    print("=" * 62)
    if not tl:
        print("  未发现时间标记")
    for pid, w in tl:
        print("  段%-2d  %s" % (pid, w))
    print("  ※ 以上是文本顺序，不等于时间顺序。若有倒叙，需人工核对是否自洽。")

    print("\n" + "=" * 62)
    print("B. 数字与量词")
    print("=" * 62)
    if not nums:
        print("  未发现")
    seen = {}
    for pid, n in nums:
        seen.setdefault(n, []).append(pid)
    for n, pids in seen.items():
        print("  %-8s 出现于段 %s" % (n, ",".join(map(str, pids))))

    print("\n" + "=" * 62)
    print("C. 代词开头的句子（可能指代不明）")
    print("=" * 62)
    if not prons:
        print("  未发现")
    for pid, s in prons:
        print("  段%-2d  %s" % (pid, s))

    # ---------- 人工标注的逻辑问题 ----------
    issues = []
    if len(sys.argv) > 2:
        rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        for r in rows:
            for it in (r.get("logic") or []):
                issues.append((r["para"], it.get("issue", ""), it.get("severity", "中")))

    print("\n" + "=" * 62)
    print("D. 逻辑问题（人工标注）")
    print("=" * 62)
    if not issues:
        print("  未标注（只表示没查出来，不等于没有）")
        s = FULL
    else:
        s = FULL
        for pid, iss, sev in issues:
            d = PEN.get(sev, 1.5)
            s -= d
            print("  段%-2d  [%s] %s   −%.1f" % (pid, sev, iss, d))
        s = max(0.0, s)

    print("\n" + "=" * 62)
    print("评分")
    print("=" * 62)
    print("  逻辑  %5.2f / %.1f   %s" % (s, FULL, "█" * int(round(s / FULL * 10))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
