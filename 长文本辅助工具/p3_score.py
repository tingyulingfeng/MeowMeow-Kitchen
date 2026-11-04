#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 落差回收：伏笔台账与回收率。

两类缺陷都要算（伏笔的两头）
  ① 收：埋了没收     标注 open_q 而 q_resolved 为 "none"
  ② 埋：该埋没埋     后文突然出现的元素，前文没铺垫 —— 标注 unplanted: ["元素名", ...]

标注约定（在 P1 标注文件里追加字段）
  q_resolved
     数字          在第几段回答的
     "intentional" 有意不答（留白），不计入未回收
     "none"        忘了收 —— 缺陷
     缺省          未标注，列出但不计分
  unplanted
     ["柿子树"]    这一段出现的元素，本应在前文埋过但没有 —— 缺陷

评分（5 分）
  5 × ( 回收率×0.6 + 距离覆盖度×0.4 ) − 每处"该埋没埋"扣 1 分，最低 0
"""
import sys

FULL = 5.0
W_RATE = 0.6
W_SPREAD = 0.4
SHORT = 2          # ≤2 段算短问答
LONG = 5           # ≥5 段算长伏笔
PENALTY_UNPLANTED = 1.0


def ledger(rows):
    """返回台账、指标与得分。"""
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

    # 该埋没埋
    unplanted = []
    for r in rows:
        for x in (r.get("unplanted") or []):
            unplanted.append((r["para"], x))

    denom = len(resolved) + len(missing)
    rate = len(resolved) / denom if denom else 1.0

    dists = [t - p_ for p_, _, t in resolved]
    n_short = sum(1 for d in dists if d <= SHORT)
    n_long = sum(1 for d in dists if d >= LONG)
    cover = 0.0
    if dists:
        cover = min(n_short, 1) * 0.5 + min(n_long, 1) * 0.5

    base = FULL * (W_RATE * rate + W_SPREAD * cover)
    s = max(0.0, base - PENALTY_UNPLANTED * len(unplanted))

    why = ("【收】回收率 %.0f%%（收 %d / 应 %d，留白 %d 不计）+ 距覆 %.0f%%（短问答 %d，长伏笔 %d）"
           "  ｜  【埋】该埋没埋 %d 处，扣 %.1f"
           % (rate * 100, len(resolved), denom, len(intentional), cover * 100,
              n_short, n_long, len(unplanted), PENALTY_UNPLANTED * len(unplanted)))

    return {"seeds": len(seeds), "resolved": resolved, "intentional": intentional,
            "missing": missing, "pending": pending, "unplanted": unplanted,
            "n_resolved": len(resolved), "n_intentional": len(intentional),
            "n_missing": len(missing), "n_unplanted": len(unplanted),
            "dists": dists, "rate": rate, "cover": cover,
            "base": base, "score": s, "why": why}


def main():
    sys.path.insert(0, ".")
    from p1_curve import load
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    L = ledger(load(sys.argv[1]))

    print("=" * 62)
    print("伏笔台账")
    print("=" * 62)
    print("  埋设 %d 条   已收 %d   有意留白 %d   真未收 %d   未标注 %d   该埋没埋 %d"
          % (L["seeds"], L["n_resolved"], L["n_intentional"], L["n_missing"],
             len(L["pending"]), L["n_unplanted"]))
    print()
    for p, q, t in L["resolved"]:
        d = t - p
        tag = "短问答" if d <= SHORT else ("长伏笔" if d >= LONG else "中距离")
        print("  段%2d 埋：%s" % (p, q))
        print("        段%2d 收   距离 %2d 段   %s" % (t, d, tag))
    for p, q in L["intentional"]:
        print("  段%2d 埋：%s" % (p, q))
        print("        有意留白（不计未回收）")
    for p, q in L["missing"]:
        print("  段%2d 埋：%s" % (p, q))
        print("        ✗ 未回收 —— 缺陷")
    for p, q in L["pending"]:
        print("  段%2d 埋：%s" % (p, q))
        print("        待标注 q_resolved")
    for p, x in L["unplanted"]:
        print("  段%2d 出现：%s" % (p, x))
        print("        ✗ 该埋没埋 —— 前文无铺垫，读者当新元素看")

    print("\n" + "=" * 62)
    print("指标与评分")
    print("=" * 62)
    if L["dists"]:
        print("  回收距离 %s   均值 %.1f   最长 %d"
              % (L["dists"], sum(L["dists"]) / len(L["dists"]), max(L["dists"])))
    print("  回收率 %.0f%%   距离覆盖度 %.0f%%" % (L["rate"] * 100, L["cover"] * 100))
    print("  基础分 %.2f  −  该埋没埋 %d 处 × %.1f = %.2f"
          % (L["base"], L["n_unplanted"], PENALTY_UNPLANTED,
             L["base"] - L["score"]))
    print()
    print("  落差回收  %.2f / %.1f   %s"
          % (L["score"], FULL, "█" * int(round(L["score"] / FULL * 10))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
