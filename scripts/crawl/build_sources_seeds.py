"""把 discover_seeds.json 转成 sources.json 条目，并合并进现有 sources.json。

- 复用现有 sources.json 里的 (university, city, tags) 元数据；
- 丢掉 javascript: 之类的非 http 入口；
- 剔除旧的「中南大学 空 pages」占位条目（入口选错导致缺失）。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_TITLE = ["招聘", "荣休", "退休", "离退", "博士后", "博后", "人才引进", "行政", "实验",
              "思政", "兼职", "客座", "外籍", "师德", "工会", "校友", "党建", "公示",
              "通知", "政策", "下载", "师德师风", "名誉", "委员会", "学术分", "学位分"]
RANK_WORDS = ["教授", "副教授", "讲师", "研究员", "副研究员", "助理教授", "助理研究员",
              "准聘", "长聘", "特聘", "高级工程师", "工程师", "实验师", "助教"]


def usable_title(text):
    if any(s in text for s in SKIP_TITLE):
        return False
    return any(w in text for w in RANK_WORDS)


def main():
    sources = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))
    disc = json.load(open(os.path.join(HERE, "discover_seeds.json"), encoding="utf-8"))

    meta = {}
    for e in sources:
        meta.setdefault(e["university"], {"city": e["city"], "tags": e["tags"]})

    new_entries = []
    for rec in disc:
        uni, school = rec["university"], rec["school"]
        info = meta.get(uni, {"city": "", "tags": []})
        entry = {"university": uni, "city": info["city"], "tags": info["tags"],
                 "school": school, "root": rec["root"], "pages": [], "status": rec["status"]}
        if rec["status"] != "ok":
            new_entries.append(entry)
            continue
        links = [f for f in rec.get("faculty_links", []) if f["url"].startswith("http")]
        seen = set()
        if links:
            primary = links[0]["url"]
            entry["entry"] = primary
            seen.add(primary)
            for tp in rec.get("title_pages", []):
                if not usable_title(tp["text"]) or tp["url"] in seen:
                    continue
                seen.add(tp["url"])
                entry["pages"].append({"url": tp["url"], "hint": tp["text"]})
            if entry["pages"]:
                entry["pages"].insert(0, {"url": primary, "hint": ""})
            else:
                entry["pages"].append({"url": primary, "hint": ""})
            for extra in links[1:3]:
                if extra["url"] in seen:
                    continue
                seen.add(extra["url"])
                entry["pages"].append({"url": extra["url"], "hint": "", "extra": True})
        new_entries.append(entry)

    # 按「学校 + 院系」替换（可重复执行：再跑一次结果不变），
    # 并清掉旧的、采不到数据的同校占位条目（入口选错留下的空壳）。
    new_keys = {(e["university"], e["school"]) for e in new_entries}
    drop_unis = {e["university"] for e in new_entries}
    kept = [e for e in sources
            if (e["university"], e["school"]) not in new_keys
            and not (e["university"] in drop_unis and not e.get("pages"))]
    kept = [e for e in kept if not (e["university"] == "中南大学" and not e.get("pages"))]

    merged = kept + new_entries
    with open(os.path.join(HERE, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)

    ready = [e for e in new_entries if e.get("pages")]
    print(f"new_entries={len(new_entries)} with_pages={len(ready)} "
          f"total_sources={len(merged)}")
    for e in new_entries:
        hint = ",".join(p.get("hint") or "主" for p in e["pages"])
        print(f"  {e['university']:<10} {e['school'][:16]:<18} "
              f"pages={len(e['pages'])} [{hint[:46]}] ({e['status']})")


if __name__ == "__main__":
    main()
