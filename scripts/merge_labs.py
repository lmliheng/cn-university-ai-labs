#!/usr/bin/env python3
"""合并 4 个采集分片 → /root/labs-site/public/data/labs.json + meta.json

校验规则（不满足的条目直接丢弃并计数，不修复、不猜测）：
  - field ∈ {人工智能, 计算机, 电子信息}
  - university / group / source 非空；source 必须是 http(s) URL
  - university 必须在目标高校表内（防止采集串校）
"""
import json, sys, collections, datetime, re
from pathlib import Path

S = Path("/root/.penguin/data/acc/agents/default_agent/scratchpad/session-2026-09-28-03-14-25-1c2127b9")
OUT = Path("/root/labs-site/data")
FIELDS = {"人工智能", "计算机", "电子信息"}

UNIVERSITIES = {
    # 北京 / 天津
    "清华大学": "北京", "北京大学": "北京", "中国人民大学": "北京", "北京航空航天大学": "北京",
    "北京理工大学": "北京", "北京邮电大学": "北京", "北京交通大学": "北京", "北京科技大学": "北京",
    "北京师范大学": "北京", "中国农业大学": "北京", "华北电力大学": "北京", "北京工业大学": "北京",
    "北京化工大学": "北京", "中国矿业大学(北京)": "北京", "南开大学": "天津", "天津大学": "天津",
    # 上海 / 江苏 / 浙江 / 安徽
    "复旦大学": "上海", "上海交通大学": "上海", "同济大学": "上海", "华东师范大学": "上海",
    "华东理工大学": "上海", "上海大学": "上海", "南京大学": "南京", "东南大学": "南京",
    "南京航空航天大学": "南京", "南京理工大学": "南京", "苏州大学": "苏州", "河海大学": "南京",
    "江南大学": "无锡", "浙江大学": "杭州", "中国科学技术大学": "合肥", "合肥工业大学": "合肥",
    # 华中 / 华南
    "武汉大学": "武汉", "华中科技大学": "武汉", "武汉理工大学": "武汉", "华中师范大学": "武汉",
    "中国地质大学(武汉)": "武汉", "中南大学": "长沙", "湖南大学": "长沙", "国防科技大学": "长沙",
    "湖南师范大学": "长沙", "中山大学": "广州", "华南理工大学": "广州", "暨南大学": "广州",
    "华南师范大学": "广州", "厦门大学": "厦门", "福州大学": "福州", "郑州大学": "郑州",
    # 西部 / 东北
    "四川大学": "成都", "电子科技大学": "成都", "西南交通大学": "成都", "重庆大学": "重庆",
    "西南大学": "重庆", "西安交通大学": "西安", "西北工业大学": "西安", "西安电子科技大学": "西安",
    "兰州大学": "兰州", "哈尔滨工业大学": "哈尔滨", "哈尔滨工程大学": "哈尔滨", "吉林大学": "长春",
    "大连理工大学": "大连", "东北大学": "沈阳", "山东大学": "济南", "云南大学": "昆明",
}
D985 = {"清华大学", "北京大学", "中国人民大学", "北京航空航天大学", "北京理工大学", "北京师范大学",
        "中国农业大学", "南开大学", "天津大学", "大连理工大学", "东北大学", "吉林大学", "哈尔滨工业大学",
        "复旦大学", "同济大学", "上海交通大学", "华东师范大学", "南京大学", "东南大学", "浙江大学",
        "中国科学技术大学", "厦门大学", "山东大学", "武汉大学", "华中科技大学", "中南大学", "湖南大学",
        "中山大学", "华南理工大学", "四川大学", "电子科技大学", "重庆大学", "西安交通大学",
        "西北工业大学", "兰州大学", "国防科技大学"}
D211 = {"北京邮电大学", "北京交通大学", "北京科技大学", "北京工业大学", "北京化工大学", "华北电力大学",
        "中国矿业大学(北京)", "南京航空航天大学", "南京理工大学", "苏州大学", "河海大学", "江南大学",
        "合肥工业大学", "武汉理工大学", "华中师范大学", "中国地质大学(武汉)", "湖南师范大学", "暨南大学",
        "华南师范大学", "福州大学", "郑州大学", "西南交通大学", "西南大学", "西安电子科技大学",
        "哈尔滨工程大学", "上海大学", "华东理工大学", "云南大学"}
ALIASES = {"中国矿业大学（北京）": "中国矿业大学(北京)", "中国地质大学（武汉）": "中国地质大学(武汉)",
           "国防科学技术大学": "国防科技大学", "北京大学信息科学技术学院": "北京大学"}

URL_RE = re.compile(r"^https?://", re.I)


def clean(x):
    return (x or "").strip()


def main():
    items, dropped = [], collections.Counter()
    per_source = collections.Counter()
    for part in sorted(S.glob("labs-part*.json")):
        try:
            data = json.loads(part.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"!! {part.name} 解析失败: {e}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            print(f"!! {part.name} 不是数组，跳过", file=sys.stderr)
            continue
        for it in data:
            if not isinstance(it, dict):
                dropped["非对象"] += 1
                continue
            uni = ALIASES.get(clean(it.get("university")), clean(it.get("university")))
            fld = clean(it.get("field"))
            grp, src = clean(it.get("group")), clean(it.get("source"))
            if uni not in UNIVERSITIES:
                dropped[f"未知学校:{uni or '空'}"] += 1
                continue
            if fld not in FIELDS:
                dropped[f"方向非法:{fld or '空'}"] += 1
                continue
            if not grp or not URL_RE.match(src):
                dropped["缺少课题组名或来源链接"] += 1
                continue
            tags = ["985", "211"] if uni in D985 else (["211"] if uni in D211 else [])
            tags.append("双一流")
            items.append({
                "university": uni,
                "city": UNIVERSITIES[uni],
                "tags": tags,
                "school": clean(it.get("school")),
                "group": grp,
                "pi": clean(it.get("pi")),
                "field": fld,
                "direction": clean(it.get("direction")),
                "homepage": clean(it.get("homepage")) if URL_RE.match(clean(it.get("homepage"))) else "",
                "source": src,
                "note": clean(it.get("note")),
            })
            per_source[part.name] += 1

    # 去重：同校 + 同课题组名
    seen, uniq = set(), []
    for it in items:
        k = (it["university"], it["group"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    uniq.sort(key=lambda x: (x["university"], x["field"], x["group"]))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "labs.json").write_text(json.dumps(uniq, ensure_ascii=False, indent=0), encoding="utf-8")

    fac = json.loads((OUT / "faculty.json").read_text(encoding="utf-8"))
    meta = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lab_count": len(uniq),
        "faculty_count": len(fac),
        "university_count": len({i["university"] for i in uniq} | {f["university"] for f in fac}),
        "lab_university_count": len({i["university"] for i in uniq}),
        "field_counts": collections.Counter(i["field"] for i in uniq),
        "sources": [
            "各校院系官网「研究团队 / 实验室 / 师资」栏目页面（每条附来源链接）",
            "CSrankings 公开数据集 github.com/emeryberger/CSrankings（按主页域名筛选中国内地高校）",
        ],
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"分片产出: {dict(per_source)}")
    print(f"丢弃: {dict(dropped)}")
    print(f"去重后课题组: {len(uniq)} 条，覆盖 {meta['lab_university_count']} 所高校")
    print(f"方向分布: {dict(meta['field_counts'])}")


if __name__ == "__main__":
    main()
