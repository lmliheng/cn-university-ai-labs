"""从院系首页出发，找出「师资队伍」入口与其下的职称分栏页面。"""
import json
import os
import re
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetcher import fetch, anchors, to_text  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

FACULTY_KW = ["师资队伍", "师资力量", "师资介绍", "教师名录", "专任教师", "教职工名录",
              "教师信息", "教师队伍", "教师风采", "师资概况", "教师主页", "师资"]

TITLE_KW = ["教授", "副教授", "讲师", "助理教授", "研究员", "副研究员", "准聘", "长聘",
            "特聘", "助理研究员", "高级工程师", "博士生导师", "硕士生导师", "博导", "硕导"]

# 明显不是教师名录的栏目
NEG_KW = ["招聘", "荣休", "退休", "离退", "博士后", "人才引进", "行政", "实验", "思政",
          "兼职", "客座", "师德", "工会", "校友", "党建", "公示", "通知", "政策", "下载"]


def pick_faculty_pages(root, html):
    """在首页里挑出师资入口候选。"""
    cands = []
    for text, url in anchors(html, root):
        if not text or len(text) > 10:
            continue
        score = 0
        for kw in FACULTY_KW:
            if kw in text:
                score = max(score, 10 + len(kw))
        if score and not any(n in text for n in NEG_KW):
            cands.append((score, text, url))
    cands.sort(key=lambda x: -x[0])
    return cands


def title_subpages(page_url, html):
    """在师资页里找出按职称分的子栏目。"""
    out = []
    for text, url in anchors(html, page_url):
        if not text or len(text) > 12:
            continue
        if any(n in text for n in NEG_KW):
            continue
        for kw in TITLE_KW:
            if kw in text:
                out.append((text, url))
                break
    # 去重保序
    seen, uniq = set(), []
    for t, u in out:
        if u not in seen:
            seen.add(u)
            uniq.append((t, u))
    return uniq


def name_links(page_url, html):
    """列表页里指向教师条目的链接（用于判断这页是不是名录）。"""
    out = []
    for text, url in anchors(html, page_url):
        if re.fullmatch(r"[\u4e00-\u9fa5·]{2,4}", text or ""):
            out.append((text, url))
    return out


def probe(student):
    uni, school, root, n = student
    status, html = fetch(root)
    if status != "ok":
        return {"university": uni, "school": school, "root": root, "status": status}
    facs = pick_faculty_pages(root, html)
    rec = {"university": uni, "school": school, "root": root, "status": "ok",
           "faculty_links": [{"text": t, "url": u} for _, t, u in facs[:4]]}
    if facs:
        fstatus, fhtml = fetch(facs[0][2])
        rec["faculty_status"] = fstatus
        if fstatus == "ok":
            subs = title_subpages(facs[0][2], fhtml)
            rec["title_pages"] = [{"text": t, "url": u} for t, u in subs]
            rec["list_has_names"] = len(name_links(facs[0][2], fhtml))
    return rec


def main():
    labs = json.load(open("/root/labs-site/data/labs.json"))
    seen = {}
    for lab in labs:
        from urllib.parse import urlparse
        u = urlparse(lab["source"])
        key = (lab["university"], lab["school"])
        seen.setdefault(key, u.scheme + "://" + u.netloc + "/")
    students = [(u, s, r, i) for i, ((u, s), r) in enumerate(sorted(seen.items()))]
    out = []
    with cf.ThreadPoolExecutor(10) as ex:
        for rec in ex.map(probe, students):
            out.append(rec)
    with open(os.path.join(HERE, "discover.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for rec in out:
        print("##", rec["university"], "|", rec["school"], "|", rec["status"],
              "| names:", rec.get("list_has_names"))
        for f in rec.get("faculty_links", []):
            print("   师资→", f["text"], f["url"])
        for t in rec.get("title_pages", [])[:20]:
            print("      职称→", t["text"], t["url"])


if __name__ == "__main__":
    main()
