#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P9 衔接（7 分）

作者理论里"衔接"管三样：时间、空间（视角）、场景转换。

  时间衔接 3   每次时间跳转有没有过渡
  视角衔接 2   视距远近变化有没有承接（远→近、内→外）
  场景转换 2   换地方有没有交代

工具的做法：把三类标记抽出来排成序列，看每次"跳"的前后有没有承接词。
没有承接词的打 ⚠，由人判断是不是故意硬切。

用法：python p9_link.py 正文段落.jsonl
"""
import json
import re
import sys

FULL = 7.0
F_TIME, F_VIEW, F_SCENE = 3.0, 2.0, 2.0

# 时间跳转（跨段跃迁，不是普通时间词）
TIME_JUMP = ["从那以后", "后来", "几年后", "多年后", "等到", "毕业后",
             "那年", "第二年", "而现在", "如今", "再后来", "长大后"]
# 时间过渡（承接用的）
TIME_LINK = ["从那以后", "后来", "几年后", "等到", "而", "如今", "现在",
             "不知不觉", "终于", "慢慢的", "渐渐地", "就这样"]

# 视角标记：远 / 近 / 内 / 外
VIEW = {
    "远": ["远远", "远处", "望去", "遥望", "天边", "对面", "山顶上"],
    "近": ["走近", "眼前", "脚下", "手边", "抬头", "低头", "门槛", "怀里", "桌上"],
    "内": ["屋里", "庙里", "院里", "破庙里", "家里", "里面"],
    "外": ["庙外", "门外", "屋外", "外面", "山上", "路上", "窗外", "车窗外"],
}

# 场景转换标记
SCENE = ["走进", "来到", "去往", "回到", "路过", "路上", "在山顶", "穿过",
         "改建", "变成", "透过车窗", "再次"]


def marks(paras, table):
    out = []
    for p in paras:
        for k, ws in table.items():
            for w in ws:
                if w in p["text"]:
                    out.append((p["para_id"], k, w))
                    break
    return out


def flat(paras, words):
    out = []
    for p in paras:
        hit = [w for w in words if w in p["text"]]
        if hit:
            out.append((p["para_id"], hit[0]))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paras = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]

    tj = flat(paras, TIME_JUMP)
    tl = flat(paras, TIME_LINK)
    vw = marks(paras, VIEW)
    sc = flat(paras, SCENE)
    tset = {pid for pid, _ in tl}

    print("=" * 62)
    print("A. 时间跳转（%d 处）" % len(tj))
    print("=" * 62)
    ok_t = 0
    for pid, w in tj:
        linked = pid in tset
        # 也算上一段有过渡词
        if not linked:
            linked = (pid - 1) in tset or (pid + 1) in tset
        if linked:
            ok_t += 1
        print("  段%-2d 「%s」  %s" % (pid, w, "有承接" if linked else "⚠ 无过渡"))

    print("\n" + "=" * 62)
    print("B. 视角标记（%d 处）" % len(vw))
    print("=" * 62)
    prev = None
    ok_v = 0
    for pid, k, w in vw:
        chg = ""
        if prev and prev[1] != k:
            linked = (pid - 1) == prev[0] or (pid - 2) == prev[0]
            if linked:
                ok_v += 1
            chg = "  %s→%s %s" % (prev[1], k, "承接" if linked else "⚠ 跳")
        print("  段%-2d [%s] 「%s」%s" % (pid, k, w, chg))
        prev = (pid, k)

    print("\n" + "=" * 62)
    print("C. 场景转换（%d 处）" % len(sc))
    print("=" * 62)
    ok_s = 0
    for pid, w in sc:
        row = next(x for x in paras if x["para_id"] == pid)
        has_bridge = any(b in row["text"] for b in ["路上", "在", "从", "到", "往"])
        if has_bridge:
            ok_s += 1
        print("  段%-2d 「%s」  %s" % (pid, w, "有交代" if has_bridge else "⚠ 无交代"))

    # ---------- 评分 ----------
    n_t, n_v, n_s = len(tj), max(len(vw) - 1, 1), len(sc)
    r_t = ok_t / n_t if n_t else 1.0
    r_v = ok_v / n_v if n_v else 1.0
    r_s = ok_s / n_s if n_s else 1.0
    s = F_TIME * r_t + F_VIEW * r_v + F_SCENE * r_s

    print("\n" + "=" * 62)
    print("D. 评分")
    print("=" * 62)
    print("  时间衔接  %4.2f / %.1f   有承接 %d / %d" % (F_TIME * r_t, F_TIME, ok_t, n_t))
    print("  场景转换  %4.2f / %.1f   有交代 %d / %d" % (F_SCENE * r_s, F_SCENE, ok_s, n_s))
    print("  视角衔接  —— / %.1f     待做（见下）" % F_VIEW)
    print("  " + "-" * 56)
    done = F_TIME * r_t + F_SCENE * r_s
    print("  %-6s %4.2f / %.1f   （视角 2 分未计入）" % ("合计", done, F_TIME + F_SCENE))
    print()
    print("  ※ 视角衔接暂不计分：现在按关键词出现就记一次切换，")
    print("    33 段能记出 18 次，明显是噪音（「庙里」「远处」出现就算一次）。")
    print("    真要做得判断「这一段的主体视角是什么」，需要段落级标注，以后再说。")
    print()
    print("  ※ 只判「有没有承接词」，判不了「接得好不好」。无过渡也可能是故意硬切。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
