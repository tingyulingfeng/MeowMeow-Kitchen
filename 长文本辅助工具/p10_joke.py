#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P10 笑料与梗（5 分）

原则（作者定）：**所有打分由工具进行。**
作者可以开人工输入窗口，但自行提供的必须联网验证，且权重较低。

  笑点密度  2   每千字有几个笑点
  笑点位置  2   笑点前面堆了铺垫没有（笑点落在铺垫之后才响）
  梗的新鲜度 1  用的是常青梗/自创梗，还是已经过时的网络梗

笑点怎么认
  用 P1 标注：功能=「释放」且方向=+1 的段落，就是笑点。
  （功能=释放但方向=-1 的是泪点，不算笑料。）

梗库
  `梗库.jsonl`，每行 {meme, kind, origin, peak, status, meaning, note}
  status: 常青 / 过时。过时的梗每用一次扣分。
  **需要定期从网络热点更新**——过时的判断靠"当前流行度"，不是永久真理。

人工输入
  标注里可写 `joke_manual: [{"where": 段号, "what": "梗", "verified": true}]`
  **verified 必须为 true 才计分，权重减半**（作者自评只作补充）。

用法：python p10_joke.py 标注文件.jsonl [梗库.jsonl]
"""
import json
import sys

FULL = 5.0
F_DENS, F_POS, F_FRESH = 2.0, 2.0, 1.0
PEN_OLD = 0.5          # 用一次过时梗的扣分
MANUAL_WEIGHT = 0.5    # 人工输入的权重


def load_memes(path):
    try:
        return {json.loads(l)["meme"]: json.loads(l)
                for l in open(path, encoding="utf-8") if l.strip()}
    except FileNotFoundError:
        return {}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    memes = load_memes(sys.argv[2] if len(sys.argv) > 2 else "梗库.jsonl")
    # 第三个参数是正文；把 text 合进标注（标注里没有正文）
    if len(sys.argv) > 3:
        body = {json.loads(l)["para_id"]: json.loads(l)["text"]
                for l in open(sys.argv[3], encoding="utf-8") if l.strip()}
        for r in rows:
            r.setdefault("text", body.get(r["para"], ""))

    n = len(rows)
    chars = sum(len(r.get("text", "")) for r in rows)
    if not chars:
        print("没有正文，请把标注和正文合并成一个文件，或用 --chars 指定字数")
        return 1

    # ---------- 笑点：功能=释放 且 方向=+1 ----------
    jokes = [r for r in rows if r.get("function") == "释放" and r.get("direction") == 1]
    print("=" * 62)
    print("A. 笑点（释放 + 向上）")
    print("=" * 62)
    for r in jokes:
        # 前面有几段同向铺垫
        i = rows.index(r)
        k, layer = i - 1, 0
        while k >= 0 and rows[k].get("direction") == 1:
            layer += 1
            k -= 1
        print("  段%-2d 前面堆了 %d 段同向铺垫  %s"
              % (r["para"], layer, "位置对" if layer >= 2 else "⚠ 铺垫不足"))
    if not jokes:
        print("  没有标注出笑点（P1 里把功能标成「释放」、方向 +1）")

    # ---------- 梗的匹配 ----------
    print("\n" + "=" * 62)
    print("B. 梗库匹配")
    print("=" * 62)
    hits = []
    for r in rows:
        for m, info in memes.items():
            if m in r.get("text", ""):
                hits.append((r["para"], m, info.get("status", "?"), info.get("kind", "")))
    if not hits:
        print("  未匹配到库里的梗（可能是自创梗，或库里没有）")
    for pid, m, st, kind in hits:
        print("  段%-2d 「%s」  %s / %s  %s"
              % (pid, m, kind, st, "✓" if st == "常青" else "⚠ 过时"))

    # ---------- 人工补充 ----------
    manual = []
    for r in rows:
        for j in (r.get("joke_manual") or []):
            manual.append((r["para"], j.get("what", ""), bool(j.get("verified"))))
    if manual:
        print("\n" + "=" * 62)
        print("C. 人工输入（权重减半，必须已验证）")
        print("=" * 62)
        for pid, what, ver in manual:
            print("  段%-2d %s  %s" % (pid, what, "已验证 ✓" if ver else "⚠ 未验证，不计分"))

    # ---------- 评分 ----------
    per_k = len(jokes) / (chars / 1000)
    if per_k >= 2:
        s_d = F_DENS
    elif per_k >= 1:
        s_d = F_DENS * 0.75
    elif per_k >= 0.5:
        s_d = F_DENS * 0.5
    else:
        s_d = F_DENS * 0.25

    pos_ok = 0
    for r in jokes:
        i = rows.index(r)
        k, layer = i - 1, 0
        while k >= 0 and rows[k].get("direction") == 1:
            layer += 1
            k -= 1
        if layer >= 2:
            pos_ok += 1
    s_p = F_POS * (pos_ok / len(jokes)) if jokes else 0.0

    old = [h for h in hits if h[2] == "过时"]
    s_f = max(0.0, F_FRESH - PEN_OLD * len(old))

    verified = [m for m in manual if m[2]]
    bonus = MANUAL_WEIGHT * (min(len(verified), 2) * 0.5)

    s = s_d + s_p + s_f + bonus
    s = min(s, FULL)

    print("\n" + "=" * 62)
    print("D. 评分")
    print("=" * 62)
    print("  笑点密度  %4.2f / %.1f   %.2f 个/千字（%d 个 / %d 字）"
          % (s_d, F_DENS, per_k, len(jokes), chars))
    print("  笑点位置  %4.2f / %.1f   %d / %d 个落在铺垫之后"
          % (s_p, F_POS, pos_ok, len(jokes)))
    print("  梗新鲜度  %4.2f / %.1f   过时梗 %d 处" % (s_f, F_FRESH, len(old)))
    if bonus:
        print("  人工补充  +%.2f       已验证 %d 条（权重 %.1f）" % (bonus, len(verified), MANUAL_WEIGHT))
    print("  " + "-" * 56)
    print("  %-6s %4.2f / %.1f" % ("合计", s, FULL))
    print()
    print("  ※ 梗库需要定期从网络热点更新——「过时」是当下的判断，不是永久真理。")
    print("  ※ 人工输入必须 verified=true 才计分，且权重减半。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
