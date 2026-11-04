#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1 度量：从逐段标注算出曲线指标。

输入 jsonl，每行：{"para", "strength" 0-3, "direction" -1/0/1, "function", "open_q"}

核心概念
  强度 = 幅度（读者被推得多狠）
  方向 = 去向（往上还是往下）
  高度 pos = 方向 × 强度   ← 这才是"过山车的高度"，范围 -3..+3
  落差 = 相邻峰谷之间的高度差，不是相邻段之间的强度差

用法：python p1_curve.py 标注文件.jsonl
"""
import json
import sys
import statistics as st


def load(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    rows.sort(key=lambda r: r["para"])
    for r in rows:
        r["pos"] = r["direction"] * r["strength"]
    return rows


def draw(rows):
    print("\n段 | 强度 | 方向 | 高度 | 功能")
    print("---+------+------+------+------")
    for r in rows:
        bar = "█" * r["strength"] + "·" * (3 - r["strength"])
        d = {1: "+1", 0: " 0", -1: "-1"}[r["direction"]]
        print("%2d | %s | %s   | %+d   | %s"
              % (r["para"], bar, d, r["pos"], r["function"]))


def plateaus(rows):
    """把高度相同的连续段并成一块，返回 [(value, start_idx, end_idx)]"""
    out = []
    for i, r in enumerate(rows):
        if out and out[-1][0] == r["pos"]:
            out[-1] = (out[-1][0], out[-1][1], i)
        else:
            out.append((r["pos"], i, i))
    return out


def zigzag(pos, th=2):
    """峰谷检测（阈值过滤）。

    只有从最近极值反向摆动 >= th 级，才确认一个拐点。
    不做过滤的话，±1 的小抖动全被当成转折——33 段能抓出 15 个"拐点"，
    那不是过山车，是噪音。

    th 的量纲是"级"，量表总幅度 6 级（-3..+3），故 th=2 约等于 1/3 振幅。
    返回 [(idx, value, kind)]，kind 交替为 峰 / 谷。
    """
    n = len(pos)
    if n < 2:
        return []
    out = []
    hi_i, hi_v = 0, pos[0]
    lo_i, lo_v = 0, pos[0]
    trend = 0                      # 0 未定 / 1 上行 / -1 下行
    for j in range(1, n):
        v = pos[j]
        if trend >= 0 and v > hi_v:
            hi_i, hi_v = j, v
        if trend <= 0 and v < lo_v:
            lo_i, lo_v = j, v
        if trend == 0:
            if hi_v - lo_v >= th:
                if hi_i > lo_i:
                    out.append((lo_i, lo_v, "谷"))
                    trend = 1
                    lo_i, lo_v = hi_i, hi_v
                    hi_i, hi_v = j, v
                else:
                    out.append((hi_i, hi_v, "峰"))
                    trend = -1
                    hi_i, hi_v = lo_i, lo_v
                    lo_i, lo_v = j, v
        elif trend == 1:
            if hi_v - v >= th:
                out.append((hi_i, hi_v, "峰"))
                trend = -1
                # 转向瞬间两个跟踪器都要重置，否则会用旧值去比新方向，谷会定偏
                hi_i, hi_v = j, v
                lo_i, lo_v = j, v
        else:
            if v - lo_v >= th:
                out.append((lo_i, lo_v, "谷"))
                trend = 1
                hi_i, hi_v = j, v
                lo_i, lo_v = j, v
    last = (hi_i, hi_v, "峰") if trend >= 0 else (lo_i, lo_v, "谷")
    if not out or out[-1][0] != last[0]:
        out.append(last)
    return out


def extrema(rows, th=2):
    return zigzag([r["pos"] for r in rows], th)


def report(rows):
    n = len(rows)
    s = [r["strength"] for r in rows]
    p = [r["pos"] for r in rows]
    ex = extrema(rows)

    print("\n" + "=" * 60)
    print("一、总量")
    print("=" * 60)
    print("  段数 %d   强度均值 %.2f   方向分布 +1:%d  0:%d  -1:%d"
          % (n, st.mean(s),
             sum(1 for r in rows if r["direction"] == 1),
             sum(1 for r in rows if r["direction"] == 0),
             sum(1 for r in rows if r["direction"] == -1)))
    hi, lo = max(p), min(p)
    print("  最高处 %+d（段 %s）" % (hi, ",".join(str(r["para"]) for r in rows if r["pos"] == hi)))
    print("  最低处 %+d（段 %s）" % (lo, ",".join(str(r["para"]) for r in rows if r["pos"] == lo)))
    print("  全程落差 = %+d − (%+d) = %d 级（量表总幅度 6 级）" % (hi, lo, hi - lo))

    print("\n" + "=" * 60)
    print("二、峰谷序列（过山车的拐点）")
    print("=" * 60)
    if not ex:
        print("  曲线单调，无拐点")
    for i, v, kind in ex:
        print("  %s  段 %2d  高度 %+d   （%s）" % (kind, rows[i]["para"], v, rows[i]["function"]))

    print("\n" + "=" * 60)
    print("三、落差：相邻峰谷之间掉了多少")
    print("=" * 60)
    if len(ex) < 2:
        print("  拐点不足，算不出落差")
    else:
        for (i1, v1, k1), (i2, v2, k2) in zip(ex, ex[1:]):
            span = rows[i2]["para"] - rows[i1]["para"]
            drop = abs(v2 - v1)
            per = drop / span if span else 0
            tag = "陡" if per >= 0.8 else ("缓" if per <= 0.35 else "中")
            print("  %s段%2d → %s段%2d   高度 %+d → %+d   落差 %d 级   跨 %d 段   %.2f 级/段  %s"
                  % (k1, rows[i1]["para"], k2, rows[i2]["para"], v1, v2, drop, span, per, tag))

    print("\n" + "=" * 60)
    print("四、节奏：拐点间隔")
    print("=" * 60)
    if len(ex) >= 2:
        gaps = [rows[b]["para"] - rows[a]["para"] for (a, _, _), (b, _, _) in zip(ex, ex[1:])]
        print("  间隔序列 %s" % gaps)
        m, sd = st.mean(gaps), st.pstdev(gaps)
        print("  均值 %.1f  标准差 %.2f  → %s"
              % (m, sd, "忽快忽慢" if sd > m * 0.6 else "比较均匀"))
        print("  %d 个拐点 / %d 段 = 平均每 %.1f 段一个拐点" % (len(ex), n, n / len(ex)))

    print("\n" + "=" * 60)
    print("五、铺垫层数 vs 落差幅度（核心比例）")
    print("=" * 60)
    if len(ex) >= 2:
        for (i1, v1, k1), (i2, v2, k2) in zip(ex, ex[1:]):
            span = rows[i2]["para"] - rows[i1]["para"]
            drop = abs(v2 - v1)
            if span >= 5 and drop <= 2:
                tag = "拖沓：%d 段只落 %d 级，速度 %.2f 级/段" % (span, drop, drop / span)
            elif span <= 2 and drop >= 3:
                tag = "突兀：%d 段落了 %d 级，速度 %.2f 级/段" % (span, drop, drop / span)
            else:
                tag = "配比正常"
            print("  %s段%2d → %s段%2d：%d 段 / %d 级  →  %s"
                  % (k1, rows[i1]["para"], k2, rows[i2]["para"], span, drop, tag))

    print("\n" + "=" * 60)
    print("六、功能分布")
    print("=" * 60)
    cnt = {}
    for r in rows:
        cnt[r["function"]] = cnt.get(r["function"], 0) + 1
    for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
        print("  %-4s %2d 段  %s" % (k, v, "█" * v))

    print("\n" + "=" * 60)
    print("七、悬置的问题（读者心里挂着什么）")
    print("=" * 60)
    qs = [(r["para"], r["open_q"]) for r in rows if r["open_q"] not in ("—", "-", "")]
    if not qs:
        print("  无")
    for pp, q in qs:
        print("  段 %2d：%s" % (pp, q))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])
    draw(rows)
    report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
