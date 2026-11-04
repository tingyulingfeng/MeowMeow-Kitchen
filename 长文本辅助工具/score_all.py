#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""总分概览：跑出已经实现的各项。未实现的项标注"未开始"，不计入合计。

已实现
  氛围铺垫 40：落差 / 节奏 / 连贯性 / 丰富度 / 配比 / 回收
  描写叙述 15：角色 / 环境 / 心理 / 事件 / 其他

用法：python score_all.py 标注文件.jsonl
"""
import sys
import io
import contextlib

sys.path.insert(0, ".")
from p1_curve import load
import p2_score
import p3_score
import p5_score

DEEP = [
    ("氛围波动落差", 7.5),
    ("节奏", 12.5),
    ("氛围变化连贯性", 5.0),
    ("氛围变化丰富度", 5.0),
    ("落差幅度与铺垫层数比例", 5.0),
]


def desc_scores(rows):
    a = p5_score.analyze(rows)
    n = a["n"]
    out = []
    for t in p5_score.TYPES:
        c = a["cnt"][t]
        ratio = c / n if n else 0
        s = (1.0 if c > 0 else 0.0) + \
            (1.0 if p5_score.RATIO_OK[0] <= ratio <= p5_score.RATIO_OK[1] else 0.0)
        long_ok = a["longest"].get(t, 0) <= p5_score.MAX_BLOCK
        f, s2 = a["first"][t], a["second"][t]
        skew = (f + s2 >= 3 and max(f, s2) >= (f + s2) * 0.8) or (f == 0 or s2 == 0)
        s += 1.0 if (long_ok and not skew) else 0.0
        out.append((t + "描写" if t != "其他" else "其他描述", s,
                    "%d 段（%.0f%%），前半 %d / 后半 %d" % (c, ratio * 100, f, s2)))
    return out, a


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])

    m = p2_score.metrics(rows)
    sc = p2_score.score(m, rows)
    led = p3_score.ledger(rows)
    dlist, a = desc_scores(rows)

    print("=" * 64)
    print("氛围铺垫 · 40 分")
    print("=" * 64)
    t1 = 0.0
    for name, full in DEEP:
        v, why = sc[name]
        t1 += v
        print("  %-12s %5.2f / %-4.1f %s" % (name, v, full, "█" * int(round(v / full * 10))))
        print("               %s" % why)
    print("  %-12s %5.2f / %-4.1f %s"
          % ("落差回收", led["score"], 5.0, "█" * int(round(led["score"] / 5 * 10))))
    print("               %s" % led["why"])
    t1 += led["score"]
    print("  " + "-" * 60)
    print("  %-12s %5.2f / 40.0   （%.0f%%）" % ("小计", t1, t1 / 40 * 100))

    print("\n" + "=" * 64)
    print("描写叙述 · 15 分")
    print("=" * 64)
    t2 = 0.0
    for name, v, why in dlist:
        t2 += v
        print("  %-8s %4.1f / 3.0  %s" % (name, v, "█" * int(round(v))))
        print("           %s" % why)
    print("  " + "-" * 60)
    print("  %-8s %5.2f / 15.0   （%.0f%%）" % ("小计", t2, t2 / 15 * 100))

    print("\n" + "=" * 64)
    print("合计（已实现 %d 分 / 总分 100）" % 55)
    print("=" * 64)
    print("  氛围铺垫 %5.2f / 40" % t1)
    print("  描写叙述 %5.2f / 15" % t2)
    print("  " + "-" * 60)
    print("  %-8s %5.2f / 55.0   （%.0f%%）" % ("合计", t1 + t2, (t1 + t2) / 55 * 100))
    print()
    print("  未开始：语言文字 15 ｜ 逻辑 10 ｜ 暗线 10 ｜ 笑料与梗 5 ｜ 衔接 5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
