#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 描写叙述（15 分）：五类占比与分布。

标注约定（在 P1 标注文件里追加字段 dtype）
  角色 / 环境 / 心理 / 事件 / 其他    —— 这一段的主体是哪种

每类 3 分，按三条判：
  ① 存在    该类至少出现 1 段
  ② 占比    落在 5%–40% 之间（不缺席，也不霸屏）
  ③ 无长块  没有超过 3 段的连续同类（避免"噎住"）

用法：python p5_score.py 标注文件.jsonl
"""
import sys

TYPES = ["角色", "环境", "心理", "事件", "其他"]
PER = 3.0
RATIO_OK = (0.05, 0.40)
MAX_BLOCK = 3


def analyze(rows):
    n = len(rows)
    cnt = {t: 0 for t in TYPES}
    pos = {t: [] for t in TYPES}
    unknown = []
    for i, r in enumerate(rows):
        t = r.get("dtype")
        if t not in cnt:
            unknown.append((r["para"], t))
            continue
        cnt[t] += 1
        pos[t].append(i)

    # 最长连续同类块
    longest, cur_t, cur_len = {}, None, 0
    for r in rows:
        t = r.get("dtype")
        if t == cur_t:
            cur_len += 1
        else:
            if cur_t in TYPES:
                longest[cur_t] = max(longest.get(cur_t, 0), cur_len)
            cur_t, cur_len = t, 1
    if cur_t in TYPES:
        longest[cur_t] = max(longest.get(cur_t, 0), cur_len)

    # 前后半分布
    half = n // 2
    first = {t: sum(1 for i in pos[t] if i < half) for t in TYPES}
    second = {t: sum(1 for i in pos[t] if i >= half) for t in TYPES}

    return {"n": n, "cnt": cnt, "pos": pos, "unknown": unknown,
            "longest": longest, "first": first, "second": second}


def main():
    sys.path.insert(0, ".")
    from p1_curve import load
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])
    a = analyze(rows)
    n = a["n"]

    print("=" * 62)
    print("五类分布")
    print("=" * 62)
    print("  类型 | 段数 | 占比 | 最长连续 | 前半 | 后半")
    print("  -----+------+------+----------+------+-----")
    for t in TYPES:
        c = a["cnt"][t]
        print("  %-4s | %4d | %3.0f%% | %8d | %4d | %4d"
              % (t, c, c / n * 100 if n else 0, a["longest"].get(t, 0),
                 a["first"][t], a["second"][t]))
    if a["unknown"]:
        print("  ⚠ 未标 dtype 的段：%s" % [p for p, _ in a["unknown"]])

    print("\n" + "=" * 62)
    print("评分：每类 3 分 = 存在 1 + 占比 1 + 分布 1")
    print("=" * 62)
    total = 0.0
    for t in TYPES:
        c = a["cnt"][t]
        ratio = c / n if n else 0
        s_exist = 1.0 if c > 0 else 0.0
        s_ratio = 1.0 if RATIO_OK[0] <= ratio <= RATIO_OK[1] else 0.0

        # 分布：不能有长块，也不能全挤在一半
        long_ok = a["longest"].get(t, 0) <= MAX_BLOCK
        f, s2 = a["first"][t], a["second"][t]
        skew = (f + s2 >= 3 and max(f, s2) >= (f + s2) * 0.8) or (f == 0 or s2 == 0)
        s_dist = 1.0 if (long_ok and not skew) else 0.0

        s = s_exist + s_ratio + s_dist
        total += s
        notes = []
        if not s_exist:
            notes.append("缺席")
        if not s_ratio:
            notes.append("占比 %.0f%% 越界(%d%%-%d%%)"
                         % (ratio * 100, RATIO_OK[0] * 100, RATIO_OK[1] * 100))
        if not long_ok:
            notes.append("连续 %d 段过长" % a["longest"].get(t, 0))
        if skew and c > 0:
            notes.append("分布偏挤（前半 %d / 后半 %d）" % (f, s2))
        print("  %-4s %4.1f / 3.0  %s%s"
              % (t, s, "█" * int(s), ("   ← " + "；".join(notes)) if notes else ""))
    print("  " + "-" * 58)
    print("  %-4s %4.1f / 15.0   （%.0f%%）" % ("合计", total, total / 15 * 100))

    # 一个额外的读数：前后半是否偏食
    print("\n" + "=" * 62)
    print("前后半对比（同一类型在前半出现几次、后半几次）")
    print("=" * 62)
    for t in TYPES:
        f, s = a["first"][t], a["second"][t]
        if f + s == 0:
            continue
        skew = ""
        if f == 0 and s > 0:
            skew = "  ← 前半完全没有"
        elif s == 0 and f > 0:
            skew = "  ← 后半完全没有"
        elif max(f, s) >= (f + s) * 0.8 and f + s >= 3:
            skew = "  ← 几乎全挤在一半"
        print("  %-4s 前半 %d  后半 %d%s" % (t, f, s, skew))
    return 0


if __name__ == "__main__":
    sys.exit(main())
