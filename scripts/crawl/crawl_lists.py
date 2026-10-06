"""按 sources.json 抓取各校师资页面，抽取出教师记录。

顺序：先试内嵌 JSON（部分 CMS 直接吐结构化字段），再试通用块解析。
列表页支持「下页 / 尾页」翻页。
"""
import json
import os
import re
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetcher import fetch, anchors, to_text  # noqa: E402
from extract import extract_best, clean_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NEXT_RE = re.compile(r"^(下页|下一页|尾页|末页|后一页)$")


def parse_embedded_json(html, base_url):
    """解析 CMS 内嵌的 var ret = [...] 名单。"""
    m = re.search(r"var\s+ret\s*=\s*(\[)", html)
    if not m:
        return []
    start = m.start(1)
    depth, i = 0, start
    while i < len(html):
        ch = html[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    raw = html[start:i + 1]
    try:
        items = json.loads(raw)
    except Exception:  # noqa: BLE001
        return []
    out = []
    import urllib.parse
    for it in items:
        if not isinstance(it, dict):
            continue
        name = clean_name(str(it.get("showTitle", "")).strip())
        if not name:
            continue
        f = it.get("fields") or {}
        title = ""
        tm = re.search(r"(教授|研究员|副教授|副研究员|讲师|助理教授|助教)", str(f.get("zc", "")))
        if tm:
            title = tm.group(1)
        direction = ""
        for key in ("kxyj", "zszy", "yjfx", "fx"):
            val = str(f.get(key, "") or "")
            dm = re.search(r"研究方向[：:]\s*(.+?)(?:\n|科研概况|研究课题|$)", val)
            if dm:
                direction = re.sub(r"\s+", " ", dm.group(1)).strip(" ；;。,")
                break
        if not direction:
            for key in ("zszy", "kxyj"):
                val = re.sub(r"\s+", " ", str(f.get(key, "") or "")).strip()
                if val:
                    direction = val[:200]
                    break
        url = str(it.get("url", "") or "")
        out.append({
            "name": name,
            "title": title,
            "title_explicit": bool(title),
            "direction": direction,
            "orcid": "",
            "email": str(f.get("yx", "") or "").strip(),
            "source": urllib.parse.urljoin(base_url, url) if url else "",
        })
    return out


def collect_page(url, hint, max_pages=20):
    """抓一页（含翻页），返回记录列表。"""
    people, visited, current = [], set(), url
    for _ in range(max_pages):
        if not current or current in visited:
            break
        visited.add(current)
        status, html = fetch(current)
        if status != "ok":
            break
        found = parse_embedded_json(html, current)
        if not found:
            found = extract_best(html, current, hint)
        people.extend(found)
        print(f"      {current[:70]} -> {len(found)}", flush=True)
        if len(found) < 3:
            with open(os.path.join(HERE, "weak_pages.txt"), "a", encoding="utf-8") as fh:
                fh.write(current + "\n")
        nxt = ""
        for text, link in anchors(html, current):
            if NEXT_RE.match(text or "") and link not in visited:
                nxt = link
                break
        current = nxt
    return people


def crawl_school(entry):
    records, page_used = [], []
    for page in entry.get("pages", []):
        people = collect_page(page["url"], page.get("hint", ""))
        page_used.append((page["url"], len(people)))
        for p in people:
            p["university"] = entry["university"]
            p["city"] = entry["city"]
            p["tags"] = entry["tags"]
            p["school"] = entry["school"]
            p["list_source"] = page["url"]
            records.append(p)
    return {"entry": entry, "records": records, "pages": page_used}


def main():
    sources = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))
    todo = [e for e in sources if e.get("pages")]
    results = []
    with cf.ThreadPoolExecutor(16) as ex:
        futures = {ex.submit(crawl_school, e): e for e in todo}
        for i, fut in enumerate(cf.as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            print(f"[{i}/{len(todo)}] {res['entry']['university']} "
                  f"{res['entry']['school'][:14]} -> {len(res['records'])}", flush=True)

    all_records = []
    for res in results:
        e = res["entry"]
        # 同一人跨页面去重，优先保留字段更全的
        best = {}
        for r in res["records"]:
            cur = best.get(r["name"])
            if cur is None or score(r) > score(cur):
                best[r["name"]] = r
        recs = list(best.values())
        all_records.extend(recs)
        hint = ",".join(p.get("hint") or "主" for p in e["pages"])
        print(f"{e['university']:<12} {e['school'][:18]:<20} {len(recs):>4}  [{hint[:40]}]")

    with open(os.path.join(HERE, "people_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(all_records, fh, ensure_ascii=False, indent=1)
    print("total", len(all_records))


def score(r):
    return sum(bool(r.get(k)) for k in ("title", "direction", "orcid", "email", "source"))


if __name__ == "__main__":
    main()
