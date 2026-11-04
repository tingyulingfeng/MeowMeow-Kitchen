#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P8 暗线（12 分 = 深度 6 + 契合度 6）

暗线是"表层故事下面的第二层"。它没法靠句式特征算出来，
但有三样东西可以抽出来给人看：

  ① 反复出现的意象：哪些词跨多段复现（暗线常靠这些符号承载）
  ② 载体是否在结尾回收：这些意象在最后几段还出不出场
  ③ 点破句：含元词（成长/过去/回忆/代价……）的句子
     —— 直接把主题说出来，说太多就是太浅，完全不说读者又看不出

用法：python p8_theme.py 正文段落.jsonl [标注.jsonl]
"""
import json
import re
import sys
from collections import defaultdict

FULL_DEPTH, FULL_FIT = 6.0, 6.0

# 元词：一旦出现，往往是在"把话说破"
META = ["成长", "长大", "成熟", "过去", "回忆", "时光", "年月", "代价",
        "失去", "离别", "告别", "童年", "小时候", "记忆", "岁月", "曾经",
        "再也", "回不去", "留不住", "变了"]

STOP = set("的了是在和就不都也很有这那个一我他她它们上下里来到去说要会能可"
           "而但却因为所以如果虽然已经还没很更最太之又与及其并且或者什么"
           "怎么这样那样一些没有不过只是就是还是")

# 虚字：n-gram 里只要含这些，基本不是"意象"，是语法碎片
FUNC = set("的了是在时候着过就都也还很更最又而与其并且或者一个些么什怎这那我他她它们"
           "有没不会能可要之已把被让给对着向从")

FN_RE = re.compile("[" + re.escape("".join(FUNC)) + "]")


def ngrams(text, n):
    out = []
    for seg in re.findall(r"[\u4e00-\u9fa5]+", text):
        for i in range(len(seg) - n + 1):
            g = seg[i:i + n]
            if all(ch in STOP for ch in g):
                continue
            out.append(g)
    return out


def imagery(paras, min_para=3):
    """跨段复现的意象：2 字与 3 字 n-gram，统计出现过的段号"""
    stat = defaultdict(set)
    for p in paras:
        for n in (2, 3):
            for g in set(ngrams(p["text"], n)):
                if FN_RE.search(g):
                    continue
                stat[g].add(p["para_id"])
    rows = [(g, sorted(ps)) for g, ps in stat.items() if len(ps) >= min_para]
    rows.sort(key=lambda x: (-len(x[1]), x[0]))
    # 去重：短串若与已选长串的段号集合相同，跳过
    kept, seen_sets = [], []
    for g, ps in rows:
        key = tuple(ps)
        if key in seen_sets and len(g) == 2:
            continue
        kept.append((g, ps))
        seen_sets.append(key)
    return kept


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paras = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    n = len(paras)
    last_ids = {p["para_id"] for p in paras[-3:]}

    print("=" * 62)
    print("A. 反复出现的意象（跨 ≥3 段）")
    print("=" * 62)
    rows = imagery(paras)
    # 3 字优先展示，去掉被更长串完全覆盖的
    shown = 0
    for g, ps in rows:
        if len(g) == 2 and any(len(h) == 3 and g in h and h in [x[0] for x in rows[:40]]
                               for h in [g] if False):
            continue
        mark = "★结尾还在" if (set(ps) & last_ids) else ""
        print("  %-6s 段 %s  %s" % (g, ",".join(map(str, ps)), mark))
        shown += 1
        if shown >= 18:
            break

    print("\n" + "=" * 62)
    print("B. 点破句（含元词的句子）")
    print("=" * 62)
    hits = []
    for p in paras:
        for s in re.split(r"[。！？…；]+", p["text"]):
            s = s.strip()
            if not s:
                continue
            w = [m for m in META if m in s]
            if w:
                hits.append((p["para_id"], w, s))
    if not hits:
        print("  未发现")
    for pid, w, s in hits:
        print("  段%-2d [%s]" % (pid, "、".join(w)))
        print("       %s" % (s if len(s) <= 46 else s[:46] + "…"))

    print("\n" + "=" * 62)
    print("C. 读数")
    print("=" * 62)
    print("  段数 %d   跨段复现的 n-gram %d 个" % (n, len(rows)))
    print("  点破句 %d 句（占 %d 段中的 %d 段）"
          % (len(hits), n, len({h[0] for h in hits})))
    print("  结尾三段回收的意象：%s"
          % ("、".join(g for g, ps in rows if set(ps) & last_ids) or "无"))

    # 人工标注
    theme = None
    if len(sys.argv) > 2:
        rows2 = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        for r in rows2:
            if r.get("theme"):
                theme = theme or []
                theme.append((r["para"], r["theme"]))

    print("\n" + "=" * 62)
    print("D. 评分（需要人工给判断）")
    print("=" * 62)
    if theme:
        for pid, t in theme:
            print("  段%-2d  %s" % (pid, t))
    print("  深度   —— / 6.0   （载体有没有第二层含义：人工判）")
    print("  契合度 —— / 6.0   （暗线与明线的对应点有几个：人工判）")
    print()
    print("  ※ 这一项工具只能抽证据，判不了。上面三样是给人看的材料。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
