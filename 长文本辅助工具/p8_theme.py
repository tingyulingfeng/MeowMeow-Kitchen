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
    paras_all = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    paras = paras_all
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

    # ---------- 作者填写的暗线（补充窗口）----------
    theme = None
    if len(sys.argv) > 2:
        rows2 = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        for r in rows2:
            if r.get("theme"):
                theme = r["theme"]
                break

    print("\n" + "=" * 62)
    print("D. 作者填写的暗线")
    print("=" * 62)
    if not theme:
        print("  （未填写。工具判不了暗线，这一项必须作者填。）")
        print("  深度   —— / 6.0")
        print("  契合度 —— / 6.0")
        return 0

    st = theme.get("statement", "").strip()
    pts = theme.get("points") or []
    print("  暗线一句话：%s" % (st or "（空）"))
    print("  对应点 %d 个：" % len(pts))
    ok_pts = 0
    for i, p in enumerate(pts, 1):
        surf = p.get("surface", "").strip()
        under = p.get("under", "").strip()
        paras = p.get("paras") or []
        # 工具核对：段号是否存在；该段正文是否真的含这个"明面"关键词
        bad = []
        for pid in paras:
            row = next((x for x in paras_all if x["para_id"] == pid), None)
            if row is None:
                bad.append("段%d 不存在" % pid)
            elif surf and surf[:2] not in row["text"] and not any(
                    k and k in row["text"] for k in p.get("keys", [])):
                bad.append("段%d 里找不到这个明面" % pid)
        state = "✓" if (surf and under and paras and not bad) else "⚠"
        if state == "✓":
            ok_pts += 1
        print("  %s %d. %s  ↔  %s   [段 %s]"
              % (state, i, surf or "（空）", under or "（没写暗面）",
                 ",".join(map(str, paras)) or "—"))
        for b in bad:
            print("        ⚠ %s" % b)

    said = theme.get("said_out_loud")
    if said is None:
        said = len(hits)

    # ---------- 评分 ----------
    # 深度：写得清 2 + 每个点都有暗面 2 + 点破控制 2
    s_state = 2.0 if st else 0.0
    s_under = 2.0 * (min(ok_pts, len(pts)) / len(pts)) if pts else 0.0
    if said <= 0:
        s_said = 2.0
    elif said <= 2:
        s_said = 1.5
    elif said <= 4:
        s_said = 1.0
    else:
        s_said = 0.5
    depth = s_state + s_under + s_said

    # 契合度：对应点数量（每条都要能核对上）
    n_ok = ok_pts
    if n_ok >= 4:
        fit = FULL_FIT
    elif n_ok == 3:
        fit = 4.5
    elif n_ok == 2:
        fit = 3.0
    elif n_ok == 1:
        fit = 1.5
    else:
        fit = 0.0

    print("\n" + "=" * 62)
    print("E. 评分")
    print("=" * 62)
    print("  深度    %4.1f / %.1f   说清了 %.0f + 暗面齐 %.1f + 点破控制 %.1f（点破 %d 句）"
          % (depth, FULL_DEPTH, s_state, s_under, s_said, said))
    print("  契合度  %4.1f / %.1f   能核对上的对应点 %d 个" % (fit, FULL_FIT, n_ok))
    print("  " + "-" * 56)
    print("  %-6s %4.1f / %.1f" % ("合计", depth + fit, FULL_DEPTH + FULL_FIT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
