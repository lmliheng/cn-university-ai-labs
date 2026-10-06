"""用 ORCID 官方公开检索接口给教师回填 ORCID。

思路：姓名转拼音（姓 / 名）→ 检索 ORCID → 只保留「机构名与本校匹配」的记录
→ 唯一命中才回填，多个候选一律留空。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "orcid_registry")
os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "cn-university-faculty-index/1.0",
      "Accept": "application/json"}

# 校名 → ORCID 记录里可能出现的机构写法
ALIASES = {
    "清华大学": ["Tsinghua University", "清华大学"],
    "北京大学": ["Peking University", "北京大学"],
    "中国人民大学": ["Renmin University of China", "中国人民大学"],
    "北京航空航天大学": ["Beihang University", "Beijing University of Aeronautics and Astronautics"],
    "北京理工大学": ["Beijing Institute of Technology"],
    "北京邮电大学": ["Beijing University of Posts and Telecommunications"],
    "北京交通大学": ["Beijing Jiaotong University"],
    "北京科技大学": ["University of Science and Technology Beijing"],
    "北京师范大学": ["Beijing Normal University"],
    "中国农业大学": ["China Agricultural University"],
    "华北电力大学": ["North China Electric Power University"],
    "北京工业大学": ["Beijing University of Technology"],
    "北京化工大学": ["Beijing University of Chemical Technology"],
    "中国矿业大学(北京)": ["China University of Mining and Technology"],
    "南开大学": ["Nankai University"],
    "天津大学": ["Tianjin University"],
    "复旦大学": ["Fudan University"],
    "上海交通大学": ["Shanghai Jiao Tong University"],
    "同济大学": ["Tongji University"],
    "华东师范大学": ["East China Normal University"],
    "华东理工大学": ["East China University of Science and Technology"],
    "上海大学": ["Shanghai University"],
    "南京大学": ["Nanjing University"],
    "东南大学": ["Southeast University"],
    "南京航空航天大学": ["Nanjing University of Aeronautics and Astronautics"],
    "苏州大学": ["Soochow University"],
    "河海大学": ["Hohai University"],
    "江南大学": ["Jiangnan University"],
    "浙江大学": ["Zhejiang University"],
    "中国科学技术大学": ["University of Science and Technology of China"],
    "合肥工业大学": ["Hefei University of Technology"],
    "武汉大学": ["Wuhan University"],
    "华中科技大学": ["Huazhong University of Science and Technology"],
    "武汉理工大学": ["Wuhan University of Technology"],
    "华中师范大学": ["Central China Normal University"],
    "中国地质大学(武汉)": ["China University of Geosciences"],
    "中南大学": ["Central South University"],
    "湖南大学": ["Hunan University"],
    "国防科技大学": ["National University of Defense Technology"],
    "湖南师范大学": ["Hunan Normal University"],
    "中山大学": ["Sun Yat-sen University", "Sun Yat Sen University"],
    "华南理工大学": ["South China University of Technology"],
    "暨南大学": ["Jinan University"],
    "华南师范大学": ["South China Normal University"],
    "厦门大学": ["Xiamen University"],
    "福州大学": ["Fuzhou University"],
    "郑州大学": ["Zhengzhou University"],
    "四川大学": ["Sichuan University"],
    "电子科技大学": ["University of Electronic Science and Technology of China"],
    "重庆大学": ["Chongqing University"],
    "西南大学": ["Southwest University"],
    "西安交通大学": ["Xi'an Jiaotong University", "Xian Jiaotong University"],
    "西北工业大学": ["Northwestern Polytechnical University"],
    "西安电子科技大学": ["Xidian University"],
    "哈尔滨工业大学": ["Harbin Institute of Technology"],
    "哈尔滨工程大学": ["Harbin Engineering University"],
    "吉林大学": ["Jilin University"],
    "大连理工大学": ["Dalian University of Technology"],
    "东北大学": ["Northeastern University"],
    "山东大学": ["Shandong University"],
    "云南大学": ["Yunnan University"],
}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def search(given, family):
    key = os.path.join(CACHE, re.sub(r"\W+", "_", f"{given}_{family}")[:80] + ".json")
    if os.path.exists(key):
        try:
            with open(key, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001 - 缓存损坏就重新抓
            pass
    query = urllib.parse.urlencode({
        "q": f"given-names:{given} AND family-name:{family}",
        "rows": 50,
    })
    url = "https://pub.orcid.org/v3.0/expanded-search/?" + query
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.load(resp)
            if not isinstance(data, dict):
                data = {}
            with open(key, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            time.sleep(0.25)
            return data
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (attempt + 1))
    return {}


def inst_matches(names, aliases):
    """机构必须与本校英文名基本一致，避免把附属医院的同名作者认成本人。"""
    targets = {norm(a) for a in aliases}
    for name in names or []:
        n = norm(name)
        if not n:
            continue
        for t in targets:
            if n == t or (n.startswith(t) and len(n) - len(t) <= 8) \
                    or (t.startswith(n) and len(t) - len(n) <= 8):
                return True
    return False


def name_matches(entry, target):
    """ORCID 记录里的姓名必须与拼音严格等价：词集合一致，或整名连写一致。"""
    given_words = [w.lower() for w in re.findall(r"[A-Za-z]+", entry.get("given-names") or "")]
    family_words = [w.lower() for w in re.findall(r"[A-Za-z]+", entry.get("family-names") or "")]
    if not given_words and not family_words:
        return False
    words = set(given_words) | set(family_words)
    if words == target:
        return True
    ours = "".join(sorted(target))
    theirs = "".join(sorted(given_words + family_words))
    return ours == theirs


def record_matches(orcid, target, aliases):
    """取 ORCID 记录本体复核：姓名与任职机构都要对得上，否则不算命中。"""
    key = os.path.join(CACHE, "record_" + re.sub(r"\W+", "_", orcid) + ".json")
    rec = None
    if os.path.exists(key):
        try:
            with open(key, encoding="utf-8") as fh:
                rec = json.load(fh)
        except Exception:  # noqa: BLE001
            rec = None
    if rec is None:
        url = "https://pub.orcid.org/v3.0/%s/record" % orcid
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    rec = json.load(resp)
                with open(key, "w", encoding="utf-8") as fh:
                    json.dump(rec, fh)
                time.sleep(0.25)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1.5 * (attempt + 1))
    if not isinstance(rec, dict):
        return False
    person = rec.get("person") or {}
    nm = person.get("name") or {}
    entry = {
        "given-names": (nm.get("given-names") or {}).get("value", ""),
        "family-names": (nm.get("family-name") or {}).get("value", ""),
    }
    if not name_matches(entry, target):
        return False
    groups = (((rec.get("activities-summary") or {}).get("employments") or {})
              .get("affiliation-group") or [])
    orgs = []
    for g in groups:
        for s in (g.get("summaries") or []):
            org = ((s.get("employment-summary") or {}).get("organization") or {}).get("name")
            if org:
                orgs.append(org)
    return inst_matches(orgs, aliases)


def lookup(person):
    tokens = name_tokens(person["name"])
    if len(tokens) < 2:
        return person, set()
    family, given = tokens[0], " ".join(tokens[1:])
    data = search(given.title(), family.title())
    aliases = ALIASES.get(person["university"], [])
    target = set(tokens)
    candidates = set()
    for r in (data.get("expanded-result") or []):
        if name_matches(r, target) and inst_matches(r.get("institution-name"), aliases):
            candidates.add(r.get("orcid-id"))
    found = {o for o in candidates if o and record_matches(o, target, aliases)}
    return person, found


_PINYIN = {}


def name_tokens(name):
    if not _PINYIN:
        return []
    parts = [p.lower() for p in _PINYIN["f"](name) if p.strip()]
    return parts if 2 <= len(parts) <= 4 else []


def main():
    try:
        sys.path.insert(0, "/root/.adelie/data/sjaaj/agents/default_agent/shared_env/pylibs")
        from pypinyin import lazy_pinyin
        _PINYIN["f"] = lazy_pinyin
    except ImportError:
        print("需要 pypinyin：pip install pypinyin")
        return

    people = json.load(open(os.path.join(HERE, "people_detail.json"), encoding="utf-8"))
    todo = [p for p in people if not p.get("orcid") and p["university"] in ALIASES]
    print("to match", len(todo), flush=True)

    matched = ambiguous = 0
    done = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for person, found in (f.result() for f in
                              [ex.submit(lookup, p) for p in todo]):
            done += 1
            if len(found) == 1:
                person["orcid"] = next(iter(found))
                person["orcid_source"] = "orcid-registry"
                matched += 1
            elif len(found) > 1:
                person["orcid_note"] = "ORCID 同名候选 %d 位，未回填" % len(found)
                ambiguous += 1
            if done % 200 == 0:
                print(f"  {done}/{len(todo)} matched={matched} ambiguous={ambiguous}", flush=True)

    print(f"orcid matched={matched} ambiguous={ambiguous}", flush=True)
    with open(os.path.join(HERE, "people_final.json"), "w", encoding="utf-8") as fh:
        json.dump(people, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
