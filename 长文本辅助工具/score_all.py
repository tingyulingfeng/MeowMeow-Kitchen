#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""氛围铺垫总分（40 分）：六项合算。

  落差 7.5 + 节奏 12.5 + 连贯性 5 + 丰富度 5 + 配比 5 + 回收 5 = 40

依赖：p1_curve（曲线）、p2_score（前五项）、p3_score（回收）
用法：python score_all.py 标注文件.jsonl
"""
import sys

sys.path.insert(0, ".")
from p1_curve import load, zigzag
import p2_score
import p3_score

CATS = [
    ("氛围波动落差", 7.5),
    ("节奏", 12.5),
    ("氛围变化连贯性", 5.0),
    ("氛围变化丰富度", 5.0),
    ("落差幅度与铺垫层数比例", 5.0),
    ("落差回收", 5.0),
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])

    m = p2_score.metrics(rows)
    sc = p2_score.score(m, rows)
    led = p3_score.ledger(rows)

    print("=" * 62)
    print("氛围铺垫 · 40 分")
    print("=" * 62)
    total = 0.0
    for name, full in CATS:
        if name == "落差回收":
            v, why = led["score"], led["why"]
        else:
            v, why = sc[name]
        total += v
        bar = "█" * int(round(v / full * 10))
        print("  %-12s %5.2f / %-4.1f %s" % (name, v, full, bar))
        print("               %s" % why)
    print("  " + "-" * 58)
    print("  %-12s %5.2f / 40.0   （%.0f%%）" % ("合计", total, total / 40 * 100))

    print("\n  曲线：%d 段 / %d 个拐点 / 最长单调段 %d 段"
          % (m["n"], m["n_turn"], m["longest"]))
    print("  伏笔：埋 %d 收 %d 留白 %d 漏 %d"
          % (led["seeds"], led["n_resolved"], led["n_intentional"], led["n_missing"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
