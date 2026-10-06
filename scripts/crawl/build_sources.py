"""生成采集配置 sources.json：每所学校 → 要抓的师资页面（列表页 + 职称分栏页）。"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetcher import fetch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# 页面标题里出现这些词 → 不是职称分栏，或属于重复/无关名单
SKIP_TITLE = ["招聘", "荣休", "退休", "离退", "博士后", "博后", "人才引进", "行政", "实验",
              "思政", "兼职", "客座", "外籍", "师德", "工会", "校友", "党建", "公示",
              "通知", "政策", "下载", "师德师风", "教师出国", "名誉"]

RANK_WORDS = ["教授", "副教授", "讲师", "研究员", "副研究员", "助理教授", "助理研究员",
              "准聘", "长聘", "特聘", "高级工程师", "工程师", "实验师", "助教"]


def is_rank_title(text):
    return any(w in text for w in RANK_WORDS)


def usable_title(text):
    if any(s in text for s in SKIP_TITLE):
        return False
    return is_rank_title(text)


def main():
    disc = json.load(open(os.path.join(HERE, "discover.json"), encoding="utf-8"))
    labs = json.load(open("/root/labs-site/data/labs.json", encoding="utf-8"))
    meta = {}
    for lab in labs:
        meta.setdefault((lab["university"], lab["school"]),
                        {"city": lab["city"], "tags": lab["tags"]})

    out = []
    for rec in disc:
        key = (rec["university"], rec["school"])
        info = meta.get(key, {})
        entry = {
            "university": rec["university"],
            "city": info.get("city", ""),
            "tags": info.get("tags", []),
            "school": rec["school"],
            "root": rec["root"],
            "pages": [],
            "status": rec["status"],
        }
        if rec["status"] != "ok":
            out.append(entry)
            continue

        seen_urls = set()
        faculty_links = rec.get("faculty_links", [])
        if faculty_links:
            primary = faculty_links[0]["url"]
            entry["entry"] = primary
            seen_urls.add(primary)
            for tp in rec.get("title_pages", []):
                if not usable_title(tp["text"]) or tp["url"] in seen_urls:
                    continue
                seen_urls.add(tp["url"])
                entry["pages"].append({"url": tp["url"], "hint": tp["text"]})
            if entry["pages"]:
                entry["pages"].insert(0, {"url": primary, "hint": ""})
            else:
                entry["pages"].append({"url": primary, "hint": ""})
            # 主入口之外的备选（例如「专任教师」与「教师名录」不同页）
            for extra in faculty_links[1:3]:
                if extra["url"] in seen_urls:
                    continue
                seen_urls.add(extra["url"])
                entry["pages"].append({"url": extra["url"], "hint": "", "extra": True})
        out.append(entry)

    with open(os.path.join(HERE, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    total = sum(len(e["pages"]) for e in out)
    ready = [e for e in out if e["pages"]]
    print(f"schools={len(out)} with_pages={len(ready)} pages={total}")
    for e in out:
        if not e["pages"]:
            print("  MISSING:", e["university"], e["school"], e["status"])
        else:
            hints = ",".join(p["hint"] or "主" for p in e["pages"])
            print(f"  {e['university']:<12} {e['school'][:20]:<22} pages={len(e['pages'])} [{hints}]")


if __name__ == "__main__":
    main()
