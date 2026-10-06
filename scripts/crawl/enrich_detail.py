"""抓每位教师的详情页，补充「研究方向 / ORCID / 邮箱 / 职称」。"""
import json
import os
import re
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetcher import fetch, to_text  # noqa: E402
from extract import (strip_chrome, extract_direction, ORCID_RE, RANK_RE,  # noqa: E402
                     clean_name)

HERE = os.path.dirname(os.path.abspath(__file__))
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def detail_fields(url, domain):
    status, html = fetch(url)
    if status != "ok" or not html:
        return {}
    clean = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"\s+", " ", " ".join(to_text(clean)))
    if not text:
        return {}
    out = {}
    direction = extract_direction(text)
    if direction:
        out["direction"] = direction
    om = ORCID_RE.search(text)
    if om:
        out["orcid"] = om.group(1)
    tm = RANK_RE.search(text[:2500])
    if tm:
        out["title"] = tm.group(1)
        out["title_explicit"] = True
    em = EMAIL_RE.search(text)
    if em:
        mail = em.group(0)
        if not re.search(r"\.(png|jpg|gif)$", mail, re.I) and "example" not in mail:
            out["email"] = mail
    return out


def work(rec):
    url = rec.get("source") or ""
    if not url.startswith("http") or url == rec.get("list_source"):
        return rec
    try:
        extra = detail_fields(url, rec.get("university", ""))
    except Exception as exc:  # noqa: BLE001
        return rec | {"detail_error": type(exc).__name__}
    if not extra:
        return rec
    merged = dict(rec)
    for key, val in extra.items():
        if not merged.get(key):
            merged[key] = val
    return merged


def main():
    src = os.path.join(HERE, "people_raw.json")
    people = json.load(open(src, encoding="utf-8"))
    todo = [p for p in people if (p.get("source") or "").startswith("http")
            and p["source"] != p.get("list_source")]
    print(f"records={len(people)} with_detail_link={len(todo)}", flush=True)
    out = []
    with cf.ThreadPoolExecutor(16) as ex:
        for i, rec in enumerate(ex.map(work, people), 1):
            out.append(rec)
            if i % 250 == 0:
                print(f"  {i}/{len(people)}", flush=True)
    with open(os.path.join(HERE, "people_detail.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    n_dir = sum(1 for r in out if r.get("direction"))
    n_orc = sum(1 for r in out if r.get("orcid"))
    n_mail = sum(1 for r in out if r.get("email"))
    print(f"done: direction={n_dir} orcid={n_orc} email={n_mail}")


if __name__ == "__main__":
    main()
