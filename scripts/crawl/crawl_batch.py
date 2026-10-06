"""只抓 sources.json 里本轮新增的理工科院系（避免重跑全校），产出 people_batch_raw.json。"""
import json
import os
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crawl_lists import crawl_school  # noqa: E402
from seeds import SEEDS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    sources = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))
    keys = {(u, s) for u, s, _ in SEEDS}
    todo = [e for e in sources if (e["university"], e["school"]) in keys and e.get("pages")]
    print(f"batch entries with pages: {len(todo)}", flush=True)

    results = []
    with cf.ThreadPoolExecutor(12) as ex:
        futures = {ex.submit(crawl_school, e): e for e in todo}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            print(f"[{i}/{len(todo)}] {res['entry']['university']} "
                  f"{res['entry']['school'][:14]} -> {len(res['records'])}", flush=True)

    all_records = []
    for res in results:
        best = {}
        for r in res["records"]:
            cur = best.get(r["name"])
            if cur is None or score(r) > score(cur):
                best[r["name"]] = r
        recs = list(best.values())
        all_records.extend(recs)
        e = res["entry"]
        print(f"{e['university']:<10} {e['school'][:18]:<20} {len(recs):>4}")

    with open(os.path.join(HERE, "people_batch_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(all_records, fh, ensure_ascii=False, indent=1)
    print("batch total", len(all_records))


def score(r):
    return sum(bool(r.get(k)) for k in ("title", "direction", "orcid", "email", "source"))


if __name__ == "__main__":
    main()
