#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P6 语言文字（11.5 分）

  错别字     1.5
  遣词造句   8.0   查错 2 + 具体化 6
  引用       2.0

具体化（6 分）
  作者的规则：多用心理/动作/环境，少用概括。
  算法：找出"情绪概括句"——含情绪概括词、但没有任何具体动作/感官词。
  具体化分 = 6 × (1 − 概括句 / 总句数)。
  概括句会逐条列出，由人判断是不是故意抒情。

引用（2 分）
  **不是越少越好**（作者修正）。考察的是用得合不合理、契不契合。
  无引用 = 0 分（这一项考的是用典能力，不用就没有这项表现）
  有引用且合理契合 = 满分
  引用不当 = 每条扣 1

用法：python p6_score.py 正文段落.jsonl [标注.jsonl]
"""
import json
import re
import sys
import statistics as st

F_TYPO, F_WORD_ERR, F_CONCRETE, F_CITE = 1.0, 2.0, 6.0, 2.0

PEN_SEMANTIC = 0.5
PEN_FLAT = 1.0
PEN_TYPO = 0.5
PEN_CITE = 1.0

TYPO = [
    ("首尾呼应", "首尾呼应"), ("喻示", "预示"),
    ("迫不急待", "迫不及待"), ("一如继往", "一如既往"),
    ("谈笑风声", "谈笑风生"), ("再接再励", "再接再厉"),
    ("不容质疑", "不容置疑"), ("按步就班", "按部就班"),
    ("默守成规", "墨守成规"), ("变本加利", "变本加厉"),
    ("出奇不意", "出其不意"), ("如愿已偿", "如愿以偿"),
    ("前扑后继", "前仆后继"), ("走头无路", "走投无路"),
    ("义无返顾", "义无反顾"), ("好高鹜远", "好高骛远"),
    ("星罗其布", "星罗棋布"), ("黄梁一梦", "黄粱一梦"),
    ("首位呼应", "首尾呼应"),
]

SEMANTIC = [
    ("偷懒", "省事"), ("累", "疲"), ("舒服", "惬意"),
    ("害怕", "恐惧"), ("好看", "漂亮"), ("开心", "高兴"),
    ("突然", "忽然"), ("大约", "左右"), ("至少", "以上"),
]

# 情绪概括词（抽象评价，不落到具体的东西上）
ABSTRACT = ["难过", "快乐", "开心", "幸福", "悲伤", "失落", "怅然",
            "美好", "温暖", "孤单", "激动", "期待", "满足", "平静",
            "愤怒", "害怕", "感动", "留恋", "怀念", "怅", "惆怅",
            "兴奋", "痛苦", "喜悦", "忧愁", "无奈", "可惜", "遗憾"]

# 具体化标记：动作、感官、具名物件
CONCRETE = ["看", "望", "听", "闻", "摸", "尝", "咬", "抱", "走", "跑",
            "站", "坐", "拿", "放", "哭", "笑", "喊", "叫", "跳", "爬",
            "蹲", "摔", "抖", "抬", "低", "转", "推", "拉", "踢", "扔",
            "香", "甜", "苦", "咸", "凉", "烫", "亮", "暗", "响",
            "门槛", "水缸", "蒲团", "屋顶", "台阶", "柿子", "哈欠",
            "眼睛", "疤", "尾巴", "毛", "爪"]

STOP = set("的了是在和就不都也很有这那个一我他她它们上下里来到去说要会能可"
           "而但却因为所以如果虽然已经还没很更最太之又与及其并且或者")


def sentences(text):
    return [s.strip() for s in re.split(r"[。！？…；]+", text) if s.strip()]


def is_abstract(s):
    if len(s) < 8:
        return False
    has_abs = any(w in s for w in ABSTRACT)
    has_con = any(w in s for w in CONCRETE)
    return has_abs and not has_con


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paras = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    full = "".join(p["text"] for p in paras)
    sl = sentences(full)

    print("=" * 62)
    print("A. 读数")
    print("=" * 62)
    print("  总字数 %d   句数 %d   平均句长 %.1f"
          % (len(full), len(sl), st.mean([len(s) for s in sl]) if sl else 0))

    # ---------- 错别字 ----------
    typo = []
    for p in paras:
        for wrong, right in TYPO:
            if wrong != right and wrong in p["text"]:
                typo.append((p["para_id"], wrong, right))

    # ---------- 查错：语义重复 ----------
    sem = []
    for p in paras:
        for a, b in SEMANTIC:
            if a in p["text"] and b in p["text"]:
                sem.append((p["para_id"], "%s / %s" % (a, b)))

    # ---------- 查错：句长过于整齐 ----------
    lens = [len(s) for s in sl]
    mean = st.mean(lens) if lens else 0
    cv = st.pstdev(lens) / mean if mean and len(lens) > 1 else 0
    flat = len(lens) >= 10 and cv < 0.35

    # ---------- 具体化 ----------
    abs_sents = [s for s in sl if is_abstract(s)]
    ratio = 1 - len(abs_sents) / len(sl) if sl else 1.0

    print("\n" + "=" * 62)
    print("B. 检查")
    print("=" * 62)
    print("  错别字 %d 处" % len(typo))
    for pid, w, r in typo:
        print("    段%-2d 「%s」→「%s」" % (pid, w, r))
    print("  语义重复 %d 处" % len(sem))
    for pid, w in sem:
        print("    段%-2d %s" % (pid, w))
    print("  句长变异系数 %.2f  %s" % (cv, "偏齐" if flat else "正常"))

    print("\n  情绪概括句 %d / %d 句（具体化率 %.0f%%）"
          % (len(abs_sents), len(sl), ratio * 100))
    for s in abs_sents:
        print("    ✗ 「%s」" % (s if len(s) <= 42 else s[:42] + "…"))

    # 含情绪词但没被判成概括的，也列出来供人工判断（机器只认最明显的）
    soft = [s for s in sl if s not in abs_sents and any(w in s for w in ABSTRACT)]
    if soft:
        print("  含情绪词但未判为概括（需人工看）%d 句：" % len(soft))
        for s in soft[:8]:
            print("    · 「%s」" % (s if len(s) <= 42 else s[:42] + "…"))

    # ---------- 引用 ----------
    cites = []
    if len(sys.argv) > 2:
        rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        for r in rows:
            for c in (r.get("citations") or []):
                cites.append((r["para"], c))

    print("\n" + "=" * 62)
    print("C. 评分")
    print("=" * 62)
    s_typo = max(0.0, F_TYPO - PEN_TYPO * len(typo))
    s_err = max(0.0, F_WORD_ERR - PEN_SEMANTIC * len(sem) - (PEN_FLAT if flat else 0.0))
    s_con = F_CONCRETE * ratio

    if not cites:
        # 无引用：这 2 分并入「具体化」。
        # 理由：引用是借别人已经落地的表达，具体化是自己落地，两者作用同向。
        # 原作品不该因为没借别人的东西而被扣分。
        s_cite = 0.0
        cap_cite = 0.0
        s_con = (F_CONCRETE + F_CITE) * ratio
        cap_con = F_CONCRETE + F_CITE
        why_cite = "无引用 —— 该项 2 分并入具体化（引用是借力，具体化是自己落地）"
    else:
        bad = [c for _, c in cites if not c.get("accurate", True) or c.get("fit", True) is False]
        s_cite = max(0.0, F_CITE - PEN_CITE * len(bad))
        cap_cite = F_CITE
        s_con = F_CONCRETE * ratio
        cap_con = F_CONCRETE
        why_cite = "%d 处引用，%d 处不当（准确度 / 契合度）" % (len(cites), len(bad))

    print("  错别字    %4.1f / %.1f   命中 %d 处" % (s_typo, F_TYPO, len(typo)))
    print("  查错      %4.1f / %.1f   语义重复 %d，句长%s"
          % (s_err, F_WORD_ERR, len(sem), "偏齐" if flat else "正常"))
    print("  具体化    %4.1f / %.1f   概括句 %d / %d%s"
          % (s_con, cap_con, len(abs_sents), len(sl),
             "（含引用让出的 2 分）" if not cites else ""))
    print("  引用      %4.1f / %.1f   %s" % (s_cite, cap_cite, why_cite))
    print("  " + "-" * 56)
    total = s_typo + s_err + s_con + s_cite
    cap = F_TYPO + F_WORD_ERR + cap_con + cap_cite
    print("  %-8s %5.1f / %.1f" % ("合计", total, cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
