#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meow_lint —— 解析质量检查器 / 结构化转换器

用法:
    python meow_lint.py lint  <解析.txt>
    python meow_lint.py build <解析.txt> [--out data/]

判定规则见同目录 RULES.md。
"""
import re
import sys
import json
import os

# ---------------------------------------------------------------- 规则表
# 通用修辞名：只给现象起名字，不给判据。出现在标题位置时要提醒。
GENERIC_LABELS = [
    "承上启下", "承接上文", "对比衬托", "推动剧情", "比喻",
    "夸张", "侧面描写", "欲扬先抑", "侧面评价", "对比体现",
]

# 术语黑名单：正确写法 -> 错误写法列表
TERM_FIXES = {
    "氛围铺垫": ["情绪铺垫"],
    "碎片化": ["碎片式"],
    "首尾呼应": ["首位呼应"],
    "预示": ["喻示"],
}

# 【缺陷】里"修法"的识别词
FIX_WORDS = ["改为", "改成", "应改", "需要改", "应该改", "补上", "删除", "添加", "替换"]

FIELDS = ["【灵感】", "构思过程", "【全局作用】", "【写法】", "缺陷", "严重缺陷"]


def clean(s):
    s = s.replace("**", "").strip()
    return re.sub(r"^>\s*", "", s).strip()


# ---------------------------------------------------------------- 解析
def parse(path):
    """把解析文本切成块。返回 [{block, segs, fields:{}, lines:{}}]"""
    raw = open(path, encoding="utf-8-sig").read().splitlines()
    blocks = []
    cur_field = None

    for ln, text in enumerate(raw, 1):
        m = re.match(r"^\*\*(.+?(?:解析|拆解)[：:]?)\*\*$", text)
        if m:
            name = m.group(1).rstrip("：:")
            # 一级小节标题（一、正文 / 二、灵感及思维链拆解）不是段落块，跳过
            if re.match(r"^[一二三四五六七八九十]、", name):
                cur_field = None
                continue
            b = {"block": name, "segs": [], "fields": {}, "lines": {},
                 "fields_lines": {}, "deprecated": "拆解" in name}
            sm = re.match(r"^第([\d\-]+)段(?:解析|拆解)$", name)
            if sm:
                p = sm.group(1).split("-")
                b["segs"] = list(range(int(p[0]), int(p[-1]) + 1))
            blocks.append(b)
            cur_field = None
            continue
        if not blocks:
            continue
        b = blocks[-1]

        fm = re.match(
            r"^-\s+\*\*(【灵感】|构思过程|【全局作用】|【写法】|严重缺陷|缺陷)\*\*[，,]?(.*)$",
            text)
        if fm:
            key = fm.group(1)
            cur_field = key
            b["fields"].setdefault(key, []).append(clean(fm.group(2)))
            b["fields_lines"].setdefault(key, []).append(ln)
            continue

        if text.startswith("- ") and cur_field:
            t = clean(text[2:])
            if not t:
                continue
            b["fields"].setdefault(cur_field, []).append(t)
            b["fields_lines"].setdefault(cur_field, []).append(ln)
            b.setdefault("raw", []).append((ln, t))
        elif text.startswith("- ") and blocks:
            # 旧格式（如「1.承上启下」）不属于任何已识别栏目，仍收进 raw 供规则检查
            t = clean(text[2:])
            if t:
                b.setdefault("raw", []).append((ln, t))

    # 反例索引
    for b in blocks:
        cfs = []
        for ln, t in b.get("raw", []):
            if t.startswith("如果") or t.startswith("若"):
                cfs.append((ln, t))
        b["cfs"] = cfs
    return blocks


# ---------------------------------------------------------------- 检查
def lint(path):
    blocks = parse(path)
    issues = []           # (level, block, line, rule, msg)

    def add(level, blk, line, rule, msg):
        issues.append((level, blk, line, rule, msg))

    if not blocks:
        add("ERROR", "-", 0, "R0", "没有解析到任何段落块（检查标题是否为 **第N段解析** 格式）")
        return issues, blocks

    for b in blocks:
        name = b["block"]
        f = b["fields"]
        has = set(f.keys())

        # R0 旧称呼
        if b.get("deprecated"):
            add("WARN", name, 0, "R6", "块标题仍用「拆解」——现行规范为「解析」")

        # R1 必填栏
        for need in ["【灵感】", "【全局作用】"]:
            if need not in has:
                add("ERROR", name, 0, "R1", f"缺必填栏 {need}")

        # R2 缺陷必须可定位到修法
        for df in ["缺陷", "严重缺陷"]:
            if df in has:
                body = "".join(f[df])
                line = b["fields_lines"][df][0]
                if not any(w in body for w in FIX_WORDS):
                    add("ERROR", name, line, "R2",
                        "【缺陷】里没有修法（找不到「改为/补上/删除」等），五步不全")

        # R3 有缺陷就该有反例
        has_defect = ("缺陷" in has) or ("严重缺陷" in has)
        if has_defect and not b["cfs"]:
            add("WARN", name, 0, "R3", "有【缺陷】但没有任何「如果……」反例")

        # R4 反例成对：既要"删了会怎样"也要"写歪了会怎样"
        if b["cfs"]:
            txts = "".join(t for _, t in b["cfs"])
            del_side = any(k in txts for k in ["删除", "删掉", "不写", "少了", "没有"])
            bad_side = any(k in txts for k in ["过于", "太", "生硬", "直白", "冗长", "拖沓", "堆砌"])
            if not del_side:
                add("WARN", name, b["cfs"][0][0], "R4", "反例只有「写歪了」一侧，缺「删了会怎样」")
            if not bad_side and has_defect:
                add("INFO", name, b["cfs"][0][0], "R4", "反例里没有「过量/过火」一侧，建议补")

        # R5 通用修辞名（要跳过行首编号，如「1.承上启下」）
        for ln, t in b.get("raw", []):
            stripped = re.sub(r"^\d+\s*[\.、]\s*", "", t)
            head = stripped.split("，")[0].split(",")[0].strip()
            for g in GENERIC_LABELS:
                if stripped.startswith(g) or head == g:
                    add("WARN", name, ln, "R5",
                        f"出现通用修辞名「{g}」——它只是给现象起名字，换成你自造的机制名或补判据")

        # R6 术语（引用旧词做自我修正的句子要跳过——那是证据，不是错误）
        META = ["改为", "有误", "说错", "更正", "改成"]
        for right, wrongs in TERM_FIXES.items():
            for w in wrongs:
                for ln, t in b.get("raw", []):
                    if w in t and not any(mk in t for mk in META):
                        add("ERROR", name, ln, "R6",
                            f"术语不一致：「{w}」应写作「{right}」")

    # R7 全文：markdown 符号残留（只提示，txt 本体允许）
    raw_lines = open(path, encoding="utf-8-sig").read().splitlines()
    n_bold = sum(1 for l in raw_lines if l.count("**") >= 2)
    n_quote = sum(1 for l in raw_lines if l.startswith(">"))
    if n_bold or n_quote:
        add("INFO", "全文", 0, "R7",
            f"含 markdown 符号（加粗行 {n_bold}、引用行 {n_quote}）——发知乎前需去符号")

    # R8 交叉引用越界
    n_deep = len(re.findall(r"^\*\*\d+\.", "\n".join(raw_lines), re.M))
    if n_deep:
        for i, l in enumerate(raw_lines, 1):
            for m in re.finditer(r"深度探索(\d+)", l):
                if int(m.group(1)) > n_deep:
                    add("ERROR", "全文", i, "R8",
                        f"引用「深度探索{m.group(1)}」，但全文只有 {n_deep} 节")

    return issues, blocks


# ---------------------------------------------------------------- 输出
def report(path, issues):
    lvl_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    issues.sort(key=lambda x: (lvl_order[x[0]], x[2]))
    counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for i in issues:
        counts[i[0]] += 1

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"ERROR {counts['ERROR']}   WARN {counts['WARN']}   INFO {counts['INFO']}\n")
    for lvl, blk, line, rule, msg in issues:
        loc = f"{blk}" + (f":{line}" if line else "")
        print(f"[{lvl:5}] {rule}  {loc}")
        print(f"        {msg}")
    return counts["ERROR"]


def parse_paragraphs(path):
    lines = open(path, encoding="utf-8-sig").read().splitlines()
    out, cur, inside = [], None, False
    for t in lines:
        if re.match(r"^\*\*一、正文\*\*", t):
            inside = True
            continue
        if re.match(r"^\*\*二、", t):
            break
        if not inside:
            continue
        m = re.match(r"^\*\*第(\d+)段", t)
        if m:
            cur = int(m.group(1))
            continue
        if cur and t.startswith(">"):
            s = clean(t[1:])
            if out and out[-1]["para_id"] == cur:
                out[-1]["text"] += s
            else:
                out.append({"para_id": cur, "text": s})
    return out


def parse_deep(path):
    lines = open(path, encoding="utf-8-sig").read().splitlines()
    out, inside = [], False
    for t in lines:
        if re.match(r"^\*\*三、深度探索\*\*", t):
            inside = True
            continue
        if re.match(r"^\*\*作者感想", t):
            break
        if not inside:
            continue
        m = re.match(r"^\*\*(\d+)\.(.+?)\*\*$", t)
        if m:
            out.append({"id": "meow-v2-deepdive-%s" % m.group(1),
                        "title": clean(m.group(2)), "body": []})
            continue
        if out:
            s = t.strip()
            if s.startswith("- "):
                s = s[2:].strip()
            if s and not s.startswith("**"):
                out[-1]["body"].append(clean(s))
    return out


def build(path, outdir):
    blocks = parse(path)
    paras = parse_paragraphs(path)
    deeps = parse_deep(path)
    pmap = {p["para_id"]: p["text"] for p in paras}
    os.makedirs(outdir, exist_ok=True)

    rows = []
    for i, b in enumerate(blocks, 1):
        f = b["fields"]
        src = "".join(pmap.get(k, "") for k in b["segs"])
        rows.append({
            "id": "meow-v2-analysis-%02d" % i,
            "block": b["block"],
            "segments": b["segs"],
            "source_text": src,
            "inspiration": f.get("【灵感】", []),
            "process": f.get("构思过程", []),
            "defects": f.get("缺陷", []) + f.get("严重缺陷", []),
            "global_role": f.get("【全局作用】", []),
            "rules": f.get("【写法】", []),
            "counterfactuals": [t for _, t in b["cfs"]],
        })

    files = [
        ("paragraphs.jsonl",
         [{"id": "meow-v2-p%02d" % p["para_id"], "para_id": p["para_id"],
           "text": p["text"]} for p in paras]),
        ("analysis.jsonl", rows),
        ("deep_dive.jsonl", deeps),
    ]
    for name, data in files:
        p = os.path.join(outdir, name)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("  写出 %-18s %d 条" % (name, len(data)))
    return rows


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "lint":
        issues, _ = lint(path)
        return 1 if report(path, issues) else 0
    if cmd == "build":
        outdir = "data"
        if "--out" in sys.argv:
            outdir = sys.argv[sys.argv.index("--out") + 1]
        build(path, outdir)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
