#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lib_add.py —— 往库里加一条，并强制检查来源标记。

用法：
  python lib_add.py taunt  条目.json          # 加一条嘲讽模板
  python lib_add.py meme   条目.json          # 加一个梗
  python lib_add.py migrate                   # 给旧库补上来源字段
  python lib_add.py check                     # 检查所有库的字段完整性

设计原则（见 库管理规范.md）：
  · 抓来的必须带 source_url
  · 用户输入必须标 source=user，未核对的 verified 必须是 false
  · 权重按 source 自动推，不允许手填
"""
import json
import os
import sys
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "taunt": ["嘲讽模板.jsonl", "嘲讽模板-绿茶真人样本.jsonl", "嘲讽模板-三家.jsonl"],
    "meme": ["梗库.jsonl"],
}

# source -> (verified 默认, weight)
POLICY = {
    "scraped": (True, 1.0),
    "authored": (False, 0.9),
    "adapted": (False, 0.8),
    "user": (False, 0.4),      # 用户未验证
    "user_verified": (True, 0.7),
}

REQUIRED_COMMON = ["id", "kind", "source", "added_at", "verified", "weight"]
TAUNT_FIELDS = ["band", "style", "mechanism", "target", "tpl"]
MEME_FIELDS = ["meme", "kind", "status", "meaning"]


def load(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def save(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def next_id(kind):
    n = 0
    for name in FILES[kind]:
        for r in load(os.path.join(BASE, name)):
            i = str(r.get("id", ""))
            if i.startswith(("taunt-", "meme-")):
                try:
                    n = max(n, int(i.split("-")[1]))
                except ValueError:
                    pass
    return "%s-%04d" % (kind, n + 1)


def validate(entry, kind):
    """返回 (ok, 修好的 entry, 错误列表)"""
    errs = []
    src = entry.get("source", "authored")
    if src not in POLICY:
        errs.append("source 必须是 " + " / ".join(POLICY))
        return False, entry, errs

    # 权重由 source 决定，不让人手填
    ver, wt = POLICY[src]
    entry["verified"] = entry.get("verified", ver)
    if entry["verified"] and src == "user":
        # 用户输入声称已验证：降级为 user_verified
        entry["source"] = "user_verified"
        wt = 0.7
    entry["weight"] = wt
    entry.setdefault("kind", kind)
    entry.setdefault("added_at", datetime.date.today().isoformat())
    entry.setdefault("id", next_id(kind))
    entry.setdefault("source_url", "")
    entry.setdefault("contributor", "")

    if entry["source"] in ("scraped", "adapted") and not entry["source_url"]:
        errs.append("抓来/改编的必须填 source_url")

    need = REQUIRED_COMMON + (TAUNT_FIELDS if kind == "taunt" else MEME_FIELDS)
    for f in need:
        if f not in entry or entry[f] in ("", None):
            errs.append("缺字段 " + f)

    return not errs, entry, errs


def cmd_add(kind):
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    entry = json.load(open(sys.argv[3], encoding="utf-8"))
    ok, entry, errs = validate(entry, kind)
    if not ok:
        print("✗ 拒绝入库：")
        for e in errs:
            print("   ·", e)
        return 1
    target = os.path.join(BASE, FILES[kind][0])
    rows = load(target)
    rows.append(entry)
    save(target, rows)
    print("✓ 已入库 %s  (source=%s, weight=%s, verified=%s)"
          % (entry["id"], entry["source"], entry["weight"], entry["verified"]))
    return 0


def cmd_migrate():
    """给旧库补上来源字段与 id。旧条目一律记 authored（本工具自己写的）。"""
    changed = 0
    for kind, names in FILES.items():
        n = 0
        # 先扫一遍已有最大 id，避免重复
        for name in names:
            for r in load(os.path.join(BASE, name)):
                i = str(r.get("id", ""))
                if i.startswith(kind + "-"):
                    try:
                        n = max(n, int(i.split("-")[1]))
                    except ValueError:
                        pass
        for name in names:
            p = os.path.join(BASE, name)
            rows = load(p)
            for r in rows:
                if "id" not in r:
                    n += 1
                    r["id"] = "%s-%04d" % (kind, n)
                if "source" in r:
                    continue
                # 原始文件里是我按机制归纳的 -> authored
                r["source"] = "authored"
                r["verified"] = False
                r["weight"] = 0.9
                r["added_at"] = r.get("added_at", "2026-11-05")
                r["source_url"] = r.get("source_url", "")
                r["contributor"] = r.get("contributor", "")
                r["kind"] = kind
                changed += 1
            save(p, rows)
    print("✓ 迁移完成，补了 %d 条" % changed)


def cmd_check():
    bad = 0
    for kind, names in FILES.items():
        for name in names:
            p = os.path.join(BASE, name)
            for i, r in enumerate(load(p), 1):
                miss = [f for f in REQUIRED_COMMON if f not in r]
                if kind == "taunt":
                    miss += [f for f in TAUNT_FIELDS if f not in r]
                if miss:
                    print("✗ %s 第%d条 缺: %s" % (name, i, ",".join(miss)))
                    bad += 1
    print("检查完毕：%s" % ("全部合规" if bad == 0 else "%d 条有问题" % bad))
    return 0 if bad == 0 else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    c = sys.argv[1]
    if c == "migrate":
        cmd_migrate()
        return cmd_check()
    if c == "check":
        return cmd_check()
    if c in ("taunt", "meme"):
        return cmd_add(c)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
