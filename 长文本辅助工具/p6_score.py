#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P6 语言文字（15 分）：错别字 3 + 遣词造句 7 + 引用 5。

三项里两项可以机器查，一项需要人工标。

错别字（3）
  扫一份常见错别字词表。命中一处扣 0.5，最低 0。
  词表在下面 TYPO，可增补。

遣词造句（7）
  ① 重复：同一段内某个 2 字以上实词出现 ≥3 次
  ② 语义重复：相邻的两个近义词同时出现（作者给过的例子：偷懒/省事、累/疲）
  ③ 句长：全篇句长过于整齐（方差过小）说明句子没有起伏
  每项按命中数扣分。

引用（5）
  从标注读 `citations`：
    {"text": "从前有座剑灵山", "kind": "作品名", "accurate": true, "cited": false}
  无引用记满分（没有可错的）。
  有引用但准确度/出处有问题逐条扣。

用法：python p6_score.py 正文段落.jsonl [标注.jsonl]
"""
import json
import re
import sys
import statistics as st

FULL_TYPO = 3.0
FULL_WORD = 7.0
FULL_CITE = 5.0

PEN_TYPO = 0.5          # 每处错别字
PEN_REPEAT = 1.0        # 每处重复
PEN_SEMANTIC = 1.0      # 每处语义重复
PEN_FLAT = 2.0          # 句长过于整齐
PEN_CITE = 2.5          # 每处引用问题

# 常见错别字：左错右对
TYPO = [
    ("首位呼应", "首尾呼应"), ("喻示", "预示"),
    ("竟然", "竟然"), ("迫不急待", "迫不及待"),
    ("一如继往", "一如既往"), ("谈笑风声", "谈笑风生"),
    ("再接再励", "再接再厉"), ("不容质疑", "不容置疑"),
    ("按步就班", "按部就班"), ("默守成规", "墨守成规"),
    ("变本加利", "变本加厉"), ("出奇不意", "出其不意"),
    ("如愿已偿", "如愿以偿"), ("前扑后继", "前仆后继"),
    ("走头无路", "走投无路"), ("义无返顾", "义无反顾"),
    ("好高鹜远", "好高骛远"), ("星罗其布", "星罗棋布"),
    ("川流不息", "川流不息"), ("黄梁一梦", "黄粱一梦"),
]

# 语义重复对（作者给的 + 常见）
SEMANTIC = [
    ("偷懒", "省事"), ("累", "疲"), ("舒服", "惬意"),
    ("害怕", "恐惧"), ("好看", "漂亮"), ("开心", "高兴"),
    ("突然", "忽然"), ("大约", "左右"), ("至少", "以上"),
]

# 虚词/停用字，不算"实词重复"
STOP = set("的了是在和就不都也很有这那个一我他她它们上下里来到去说要会能可"
           "而但却因为所以如果虽然已经还没很更最太之又与及其并且或者")

CITE_PEN = PEN_CITE


def sentences(text):
    return [s for s in re.split(r"[。！？…；]+", text) if s.strip()]


def words(text):
    """粗略切词：连续 2 个以上汉字当作一个词"""
    return re.findall(r"[\u4e00-\u9fa5]{2,}", text)


def check(paras):
    full = "".join(p["text"] for p in paras)
    issues = {"typo": [], "repeat": [], "semantic": [], "flat": []}

    # ① 错别字
    for wrong, right in TYPO:
        for p in paras:
            if wrong in p["text"]:
                issues["typo"].append((p["para_id"], wrong, right))

    # ② 段内重复
    for p in paras:
        cnt = {}
        for w in words(p["text"]):
            cnt[w] = cnt.get(w, 0) + 1
        for w, c in cnt.items():
            if c >= 3 and not all(ch in STOP for ch in w):
                issues["repeat"].append((p["para_id"], w, c))

    # ③ 语义重复（同段内近义并列）
    for p in paras:
        for a, b in SEMANTIC:
            if a in p["text"] and b in p["text"]:
                issues["semantic"].append((p["para_id"], "%s / %s" % (a, b)))

    # ④ 句长
    sl = [len(s) for s in sentences(full)]
    mean = st.mean(sl) if sl else 0
    sd = st.pstdev(sl) if len(sl) > 1 else 0
    cv = sd / mean if mean else 0
    if len(sl) >= 10 and cv < 0.35:
        issues["flat"].append((0, "句长变异系数 %.2f（过于整齐）" % cv, 0))

    # ⑤ 超长句（一句 45 字以上，读起来要断气）
    long_sents = [(i + 1, s) for i, s in enumerate(sentences(full)) if len(s) > 45]

    # ⑥ 全文高频实词（提示用，不扣分；专有名词除外）
    freq = {}
    for w in words(full):
        if all(ch in STOP for ch in w):
            continue
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:6]

    # ⑦ 相邻段开头重复（排比是手法，但超过 3 段就是单调）
    heads = []
    for p in paras:
        t = p["text"].strip()
        heads.append(t[:3] if len(t) >= 3 else t)
    run, run_head, max_run, best = 1, heads[0] if heads else "", 1, ""
    for i in range(1, len(heads)):
        if heads[i] == run_head:
            run += 1
            if run > max_run:
                max_run, best = run, run_head
        else:
            run, run_head = 1, heads[i]
    dup_head = (best, max_run) if max_run >= 3 else None

    return {"full": full, "sl": sl, "cv": cv, "issues": issues,
            "long": long_sents, "freq": top, "dup_head": dup_head}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    paras = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    R = check(paras)
    full, sl, cv, iss = R["full"], R["sl"], R["cv"], R["issues"]

    print("=" * 62)
    print("A. 客观读数")
    print("=" * 62)
    print("  总字数 %d   句数 %d   平均句长 %.1f   句长变异系数 %.2f"
          % (len(full), len(sl), st.mean(sl) if sl else 0, cv))
    print("  最长句 %d 字   最短句 %d 字"
          % (max(sl) if sl else 0, min(sl) if sl else 0))

    print("\n" + "=" * 62)
    print("B. 检查结果")
    print("=" * 62)
    if iss["typo"]:
        for pid, w, r in iss["typo"]:
            print("  错别字  段%-2d  「%s」应为「%s」" % (pid, w, r))
    else:
        print("  错别字  未发现")
    if iss["repeat"]:
        for pid, w, c in iss["repeat"]:
            print("  重复    段%-2d  「%s」出现 %d 次" % (pid, w, c))
    else:
        print("  重复    未发现")
    if iss["semantic"]:
        for pid, w in iss["semantic"]:
            print("  语义重复 段%-2d  %s" % (pid, w))
    else:
        print("  语义重复 未发现")
    if iss["flat"]:
        print("  句长    %s" % iss["flat"][0][1])
    else:
        print("  句长    起伏正常（CV %.2f ≥ 0.35）" % cv)

    print("\n  超长句（>45 字）：%d 处" % len(R["long"]))
    for i, s in R["long"][:5]:
        print("    第%d句（%d 字）：%s…" % (i, len(s), s[:30]))
    print("  全文高频实词：%s" % "、".join("%s×%d" % (w, c) for w, c in R["freq"]))
    if R["dup_head"]:
        print("  相邻段开头重复：「%s」连续 %d 段" % R["dup_head"])
    else:
        print("  相邻段开头重复：未超过 3 段")

    # 引用
    cites = []
    if len(sys.argv) > 2:
        rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        for r in rows:
            for c in (r.get("citations") or []):
                cites.append((r["para"], c))

    print("\n" + "=" * 62)
    print("C. 评分")
    print("=" * 62)
    s1 = max(0.0, FULL_TYPO - PEN_TYPO * len(iss["typo"]))
    s2 = max(0.0, FULL_WORD - PEN_SEMANTIC * len(iss["semantic"])
             - (PEN_FLAT if iss["flat"] else 0))
    if cites:
        bad = [c for _, c in cites if not c.get("accurate", True) or not c.get("cited", True)]
        s3 = max(0.0, FULL_CITE - CITE_PEN * len(bad))
        why3 = "%d 处引用，%d 处有问题" % (len(cites), len(bad))
    else:
        s3 = FULL_CITE
        why3 = "无引用（没有可错的）"

    print("  错别字    %4.1f / 3.0   %s" % (s1, "命中 %d 处" % len(iss["typo"])))
    print("  遣词造句  %4.1f / 7.0   语义重复 %d / 句长%s"
          % (s2, len(iss["semantic"]), "偏齐" if iss["flat"] else "正常"))
    print("  引用      %4.1f / 5.0   %s" % (s3, why3))
    print("  " + "-" * 56)
    print("  %-8s %5.1f / 15.0" % ("合计", s1 + s2 + s3))
    print()
    print("  ※ 重复词、超长句、段首重复只作提示，不扣分——")
    print("    主题词复现和手法性排比都会命中，机器分不清是手法还是毛病。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
