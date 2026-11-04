#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 落差回收：吃 P1 的 open_q 列，算伏笔台账与回收率。

标注约定（在 P1 标注文件里追加一个字段 `q_resolved`）
  数字         = 在第几段回答的
  "intentional"= 作者有意不答（留白），不计入未回收
  "none"       = 忘了收（这才是缺陷）
  缺省         = 未标注，按"待查"处理，不计分但会列出来

指标
  埋了几条 / 收了几条 / 有意留白几条 / 真未收几条
  回收距离 = 回答段 − 埋设段
  距离分布：短问答（≤2 段）与长伏笔（≥5 段）各有几条

评分（落差回收 5 分）
  回收率  占 60%   = 已收 /（已收 + 真未收），有意留白不算
  距离覆盖占 40%   = 短问答与长伏笔都出现才满分（只短=没悬念，只长=读者会忘）

用法：python p3_score.py 标注文件.jsonl
"""
import json
import sys
import statistics as st

sys.path.insert(0, ".")
from p1_curve import load

FULL = 5.0
W_RATE = 0.6
W_SPREAD = 0.4
SHORT = 2          # ≤2 段算短问答
LONG = 5           # ≥5 段算长伏笔


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])

    seeds = [(r["para"], r["open_q"]) for r in rows
             if r["open_q"] not in ("—", "-", "")]
    resolved, intentional, missing, pending = [], [], [], []

    for p, q in seeds:
        r = next(x for x in rows if x["para"] == p)
        v = r.get("q_resolved")
        if v is None:
            pending.append((p, q))
        elif v == "intentional":
            intentional.append((p, q))
        elif v == "none":
            missing.append((p, q))
        else:
            resolved.append((p, q, int(v)))

    print("=" * 62)
    print("伏笔台账")
    print("=" * 62)
    print("  埋设 %d 条   已收 %d   有意留白 %d   真未收 %d   未标注 %d"
          % (len(seeds), len(resolved), len(intentional), len(missing), len(pending)))
    print()
    for p, q, t in resolved:
        d = t - p
        tag = "短问答" if d <= SHORT else ("长伏笔" if d >= LONG else "中距离")
        print("  段%2d 埋：%s" % (p, q))
        print("        段%2d 收   距离 %2d 段   %s" % (t, d, tag))
    for p, q in intentional:
        print("  段%2d 埋：%s" % (p, q))
        print("        有意留白（不计未回收）")
    for p, q in missing:
        print("  段%2d 埋：%s" % (p, q))
        print("        ✗ 未回收——这是缺陷")
    for p, q in pending:
        print("  段%2d 埋：%s" % (p, q))
        print("        待标注 q_resolved")

    # ---------- 指标 ----------
    denom = len(resolved) + len(missing)
    rate = len(resolved) / denom if denom else 1.0

    dists = [t - p for p, _, t in resolved]
    n_short = sum(1 for d in dists if d <= SHORT)
    n_long = sum(1 for d in dists if d >= LONG)
    cover = 0.0
    if dists:
        cover = min(n_short / 1, 1.0) * 0.5 + min(n_long / 1, 1.0) * 0.5

    print("\n" + "=" * 62)
    print("指标")
    print("=" * 62)
    if dists:
        print("  回收距离 %s   均值 %.1f   最短 %d   最长 %d"
              % (dists, st.mean(dists), min(dists), max(dists)))
    else:
        print("  回收距离 —")
    print("  短问答（≤%d段）%d 条   长伏笔（≥%d段）%d 条" % (SHORT, n_short, LONG, n_long))
    print("  回收率 %.0f%%（已收 %d / 应收 %d，有意留白不计）"
          % (rate * 100, len(resolved), denom))
    print("  距离覆盖度 %.0f%%（短问答与长伏笔都有才满分）" % (cover * 100))

    s = FULL * (W_RATE * rate + W_SPREAD * cover)
    print("\n" + "=" * 62)
    print("评分")
    print("=" * 62)
    print("  落差回收  %.2f / %.1f   %s"
          % (s, FULL, "█" * int(round(s / FULL * 10))))
    print("            回收率 %.0f%%×%.1f + 距离覆盖 %.0f%%×%.1f"
          % (rate * 100, W_RATE, cover * 100, W_SPREAD))
    return 0


def ledger(rows):
    """返回伏笔台账与得分，供其他脚本调用。"""
    seeds = [(r["para"], r["open_q"]) for r in rows
             if r["open_q"] not in ("—", "-", "")]
    resolved, intentional, missing, pending = [], [], [], []
    for p_, q in seeds:
        r = next(x for x in rows if x["para"] == p_)
        v = r.get("q_resolved")
        if v is None:
            pending.append((p_, q))
        elif v == "intentional":
            intentional.append((p_, q))
        elif v == "none":
            missing.append((p_, q))
        else:
            resolved.append((p_, q, int(v)))
    denom = len(resolved) + len(missing)
    rate = len(resolved) / denom if denom else 1.0
    dists = [t - p_ for p_, _, t in resolved]
    n_short = sum(1 for d in dists if d <= SHORT)
    n_long = sum(1 for d in dists if d >= LONG)
    cover = 0.0
    if dists:
        cover = min(n_short, 1) * 0.5 + min(n_long, 1) * 0.5
    s = FULL * (W_RATE * rate + W_SPREAD * cover)
    return {"seeds": len(seeds), "resolved": resolved, "intentional": intentional,
            "missing": missing, "pending": pending, "n_resolved": len(resolved),
            "n_intentional": len(intentional), "n_missing": len(missing),
            "dists": dists, "rate": rate, "cover": cover, "score": s,
            "why": "回收率 %.0f%%（收 %d / 应 %d，留白不计）+ 距覆 %.0f%%（短问答 %d，长伏笔 %d）"
                   % (rate * 100, len(resolved), denom, cover * 100, n_short, n_long)}


if __name__ == "__main__":
    sys.exit(main())
