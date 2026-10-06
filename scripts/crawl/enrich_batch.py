"""对本轮新增院系抓取的记录抓详情页，补研究方向 / ORCID / 邮箱 / 职称。"""
import json
import os
import concurrent.futures as cf

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_detail import work  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    people = json.load(open(os.path.join(HERE, "people_batch_raw.json"), encoding="utf-8"))
    todo = [p for p in people if (p.get("source") or "").startswith("http")
            and p["source"] != p.get("list_source")]
    print(f"records={len(people)} with_detail_link={len(todo)}", flush=True)
    out = []
    with cf.ThreadPoolExecutor(16) as ex:
        for i, rec in enumerate(ex.map(work, people), 1):
            out.append(rec)
            if i % 250 == 0:
                print(f"  {i}/{len(people)}", flush=True)
    with open(os.path.join(HERE, "people_batch_detail.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("direction", sum(1 for r in out if r.get("direction")),
          "orcid", sum(1 for r in out if r.get("orcid")),
          "email", sum(1 for r in out if r.get("email")))


if __name__ == "__main__":
    main()
