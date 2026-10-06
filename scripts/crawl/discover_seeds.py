"""对给定院系首页种子跑「师资入口 + 职称分栏」发现，产出 discover_seeds.json。"""
import json
import os
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetcher import fetch  # noqa: E402
from discover import pick_faculty_pages, title_subpages, name_links  # noqa: E402
from seeds import SEEDS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def probe(seed):
    uni, school, root = seed
    status, html = fetch(root)
    rec = {"university": uni, "school": school, "root": root, "status": status}
    if status != "ok":
        return rec
    facs = pick_faculty_pages(root, html)
    rec["faculty_links"] = [{"text": t, "url": u} for _, t, u in facs[:4]]
    if facs:
        fstatus, fhtml = fetch(facs[0][2])
        rec["faculty_status"] = fstatus
        if fstatus == "ok":
            rec["title_pages"] = [{"text": t, "url": u}
                                  for t, u in title_subpages(facs[0][2], fhtml)]
            rec["list_has_names"] = len(name_links(facs[0][2], fhtml))
    return rec


def main():
    with cf.ThreadPoolExecutor(8) as ex:
        out = list(ex.map(probe, SEEDS))
    with open(os.path.join(HERE, "discover_seeds.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for rec in out:
        print("##", rec["university"], "|", rec["school"], "|", rec["status"],
              "| names:", rec.get("list_has_names"))
        for f in rec.get("faculty_links", []):
            print("   师资→", f["text"], f["url"])
        for t in rec.get("title_pages", [])[:24]:
            print("      职称→", t["text"], t["url"])


if __name__ == "__main__":
    main()
