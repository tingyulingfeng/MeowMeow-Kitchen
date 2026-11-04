#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 指标与评分：吃 P1 的标注，算出氛围铺垫那一大项的原始指标。

设计原则
  · 所有指标都从标注直接算出来，不含"感觉"
  · 分档公式写死在 SCORE 里，参数可调；调整前先看原始数值
  · 输出分两部分：A 原始指标（客观），B 换算分数（主观，待作者确认）

用法：python p2_score.py 标注文件.jsonl
"""
import json
import sys
import math
import statistics as st

sys.path.insert(0, ".")
from p1_curve import load, zigzag


# ================================================================
# 分档参数（作者可调；调完要写进报告，否则不可复现）
# ================================================================
SCORE = {
    # 氛围波动落差 7.5 分：最大落差 + 大落差个数
    "落差": {"full": 7.5,
             "d_max_full": 6,      # 最大落差达到几级算满（量表满幅 6）
             "big_th": 4,          # 多少级算"大落差"
             "big_full": 3,        # 大落差达到几个算满
             "w_max": 0.5, "w_big": 0.5},

    # 节奏 12.5 分：拐点间隔的变异系数 + 拐点密度
    "节奏": {"full": 12.5,
             "cv_best": (0.6, 1.2),   # 理想变异系数区间（太低=平，太高=乱）
             "cv_zero": (0.15, 1.8),  # 超出此范围得 0
             "density_best": (0.15, 0.35),  # 理想拐点密度（拐点/段数）
             "density_zero": (0.05, 0.6),
             "w_cv": 0.6, "w_den": 0.4},

    # 氛围变化连贯性 5 分：无载体跳变，每处扣分
    "连贯性": {"full": 5, "jump_th": 4, "jump_span": 1, "penalty": 1.0},

    # 氛围变化丰富度 5 分：功能分布的归一化熵
    "丰富度": {"full": 5},

    # 落差幅度与铺垫层数比例 5 分：每处落差的 段/级 是否落在合理区间
    "配比": {"full": 5, "ok": (0.6, 2.0), "penalty": 1.0},
}


def between(x, r):
    return r[0] <= x <= r[1]


def ramp(x, best, zero):
    """把 x 映射到 0..1：落在 best 区间内得 1，越接近 zero 越趋 0"""
    if between(x, best):
        return 1.0
    if x < best[0]:
        return max(0.0, (x - zero[0]) / (best[0] - zero[0]))
    return max(0.0, (zero[1] - x) / (zero[1] - best[1]))


def metrics(rows, th=2):
    n = len(rows)
    pos = [r["pos"] for r in rows]
    ex = zigzag(pos, th)

    # ---------- 落差 ----------
    drops = []
    for (i1, v1, k1), (i2, v2, k2) in zip(ex, ex[1:]):
        drops.append({"from": rows[i1]["para"], "to": rows[i2]["para"],
                      "v1": v1, "v2": v2,
                      "drop": abs(v2 - v1),
                      "span": rows[i2]["para"] - rows[i1]["para"]})
    dvals = [d["drop"] for d in drops]
    d_max = max(dvals) if dvals else 0
    d_big = sum(1 for d in dvals if d >= SCORE["落差"]["big_th"])

    # ---------- 节奏 ----------
    gaps = [d["span"] for d in drops]
    n_turn = len(ex)
    density = n_turn / n if n else 0
    if len(gaps) >= 2 and st.mean(gaps) > 0:
        cv = st.pstdev(gaps) / st.mean(gaps)
    else:
        cv = 0.0

    # 最长单调段（一直没有拐点的连续段）
    longest = max(gaps) if gaps else n

    # ---------- 连贯性：无载体跳变 ----------
    jumps = []
    for d in drops:
        if d["drop"] >= SCORE["连贯性"]["jump_th"] and d["span"] <= SCORE["连贯性"]["jump_span"]:
            # 看落点那一段是否标注为"转折"——有载体就不算跳变
            target = next((r for r in rows if r["para"] == d["to"]), None)
            has_carrier = target and target["function"] in ("转折", "释放", "留白")
            jumps.append({**d, "carrier": bool(has_carrier)})

    # ---------- 丰富度：功能熵 ----------
    cnt = {}
    for r in rows:
        cnt[r["function"]] = cnt.get(r["function"], 0) + 1
    H = 0.0
    for v in cnt.values():
        p = v / n
        H -= p * math.log(p)
    H_norm = H / math.log(len(cnt)) if len(cnt) > 1 else 0.0

    # ---------- 配比 ----------
    ratios = []
    for d in drops:
        r_ = d["span"] / d["drop"] if d["drop"] else 999
        ratios.append({"from": d["from"], "to": d["to"], "drop": d["drop"],
                       "span": d["span"], "ratio": r_,
                       "ok": between(r_, SCORE["配比"]["ok"])})

    return {"n": n, "ex": ex, "drops": drops, "d_max": d_max, "d_big": d_big,
            "dvals": dvals, "gaps": gaps, "n_turn": n_turn, "density": density,
            "cv": cv, "longest": longest, "jumps": jumps,
            "entropy": H_norm, "func_cnt": cnt, "ratios": ratios}


def score(m):
    out = {}

    # 落差
    cfg = SCORE["落差"]
    a = min(m["d_max"] / cfg["d_max_full"], 1.0)
    b = min(m["d_big"] / cfg["big_full"], 1.0)
    out["氛围波动落差"] = (cfg["full"] * (cfg["w_max"] * a + cfg["w_big"] * b),
                          "最大落差 %d 级 / 大落差(≥%d级) %d 个"
                          % (m["d_max"], cfg["big_th"], m["d_big"]))

    # 节奏
    cfg = SCORE["节奏"]
    a = ramp(m["cv"], cfg["cv_best"], cfg["cv_zero"])
    b = ramp(m["density"], cfg["density_best"], cfg["density_zero"])
    out["节奏"] = (cfg["full"] * (cfg["w_cv"] * a + cfg["w_den"] * b),
                   "变异系数 %.2f / 拐点密度 %.2f（每 %.1f 段一个）"
                   % (m["cv"], m["density"], 1 / m["density"] if m["density"] else 0))

    # 连贯性
    cfg = SCORE["连贯性"]
    bad = [j for j in m["jumps"] if not j["carrier"]]
    out["氛围变化连贯性"] = (max(0.0, cfg["full"] - cfg["penalty"] * len(bad)),
                             "无载体跳变 %d 处" % len(bad))

    # 丰富度
    cfg = SCORE["丰富度"]
    out["氛围变化丰富度"] = (cfg["full"] * m["entropy"],
                             "功能熵 %.3f（%d 种功能）"
                             % (m["entropy"], len(m["func_cnt"])))

    # 配比：规则未定，暂不计分（见 P2-报告.md「未解决」一节）
    out["落差幅度与铺垫层数比例"] = (None,
                                 "规则待定——统一区间会把「慢爬坡」「急收」这类正常手法误判为越界")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])
    m = metrics(rows)

    print("=" * 62)
    print("A. 原始指标（客观，从标注直接算出）")
    print("=" * 62)
    print("  段数 %d   拐点 %d 个   最长单调段 %d 段" % (m["n"], m["n_turn"], m["longest"]))
    print("  落差序列（级）%s" % m["dvals"])
    print("    合计 %d 级  最大 %d 级  ≥4 级的有 %d 个"
          % (sum(m["dvals"]), m["d_max"], m["d_big"]))
    print("  拐点间隔 %s" % m["gaps"])
    print("    均值 %.1f  标准差 %.1f  变异系数 %.2f"
          % (st.mean(m["gaps"]) if m["gaps"] else 0,
             st.pstdev(m["gaps"]) if len(m["gaps"]) > 1 else 0, m["cv"]))
    print("  功能分布 %s" % ", ".join("%s%d" % (k, v) for k, v in
                                     sorted(m["func_cnt"].items(), key=lambda x: -x[1])))
    print("  功能熵 %.3f（归一化，1=完全均匀）" % m["entropy"])

    print("\n  逐处落差明细：")
    for d, r in zip(m["drops"], m["ratios"]):
        print("    段%2d→%2d  高度 %+d→%+d  落差 %d 级  跨 %d 段  %.2f 段/级  %s"
              % (d["from"], d["to"], d["v1"], d["v2"], d["drop"], d["span"],
                 r["ratio"], "OK" if r["ok"] else "越界"))

    if m["jumps"]:
        print("\n  大幅跳变（≥%d 级且 ≤%d 段）：" % (SCORE["连贯性"]["jump_th"],
                                                SCORE["连贯性"]["jump_span"]))
        for j in m["jumps"]:
            print("    段%2d→%2d  落差 %d 级  落点功能=%s  %s"
                  % (j["from"], j["to"], j["drop"],
                     next(r["function"] for r in rows if r["para"] == j["to"]),
                     "有载体 OK" if j["carrier"] else "无载体，算跳变"))

    print("\n" + "=" * 62)
    print("B. 换算分数（主观，分档值待作者确认）")
    print("=" * 62)
    sc = score(m)
    total, fullsum = 0.0, 0.0
    for k, (v, why) in sc.items():
        key = {"氛围波动落差": "落差", "节奏": "节奏", "氛围变化连贯性": "连贯性",
               "氛围变化丰富度": "丰富度",
               "落差幅度与铺垫层数比例": "配比"}[k]
        full = SCORE[key]["full"]
        if v is None:
            print("  %-12s %5s / %-4.1f  待定" % (k, "—", full))
            print("               %s" % why)
            continue
        total += v
        fullsum += full
        bar = "█" * int(round(v / full * 10))
        print("  %-12s %5.2f / %-4.1f  %s" % (k, v, full, bar))
        print("               %s" % why)
    print("  " + "-" * 58)
    print("  %-12s %5.2f / %-4.1f   （不含待定的「配比」5 分）"
          % ("小计", total, fullsum))
    return 0


if __name__ == "__main__":
    sys.exit(main())
