"""把采集结果整理成交付数据集 data/faculty.json + meta.json + CSV。

校验规则（不满足的条目丢弃并计数，不修复、不猜测）：
  - name 必须是 2~4 个汉字（不含站名、栏目词）
  - university 必须在目标高校表内
  - 同一学校内按姓名去重，保留字段更全的一条
  - 姓名若横跨 ≥3 所学校，判定为站点栏目词，整名丢弃
  - 至少要有一条实质信息（职称或研究方向），否则丢弃
"""
import collections
import csv
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "data")
WORK = HERE
UNIVERSITIES = {}


def load_universities():
    """目标高校表来自采集配置（sources.json）。"""
    path = os.path.join(WORK, "sources.json")
    for entry in json.load(open(path, encoding="utf-8")):
        UNIVERSITIES[entry["university"]] = {
            "city": entry["city"], "tags": entry["tags"], "school": entry["school"]}


RANK_MAP = [
    ("副教授", ["副教授", "准聘副教授", "预聘副教授"]),
    ("助理教授", ["助理教授", "预聘助理教授", "准聘助理教授"]),
    ("讲师", ["讲师"]),
    ("副研究员", ["副研究员", "特任副研究员", "特聘副研究员"]),
    ("助理研究员", ["助理研究员", "特聘助理研究员"]),
    ("研究员", ["研究员", "特任研究员", "特聘研究员"]),
    ("教授", ["教授", "特聘教授", "长聘教授", "准聘教授"]),
    ("助教", ["助教"]),
]

NAME_RE = re.compile(r"^[\u4e00-\u9fa5·]{2,4}$")
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
BAD_NAME = ["学院", "大学", "中心", "实验", "研究所", "研究院", "团队", "系所", "学部",
            "委员会", "办公室", "支部", "党委", "工会", "校友", "基金", "基地", "平台",
            "首页", "更多", "名单", "队伍", "导师", "职称", "教授", "简历", "主页", "领导",
            "设置", "建设", "概况", "链接", "公示", "办公", "系统", "邮箱", "门户", "部门",
            "机构", "学会", "协会", "项目", "课程", "教学", "成果", "动态", "快讯", "方向",
            "培养", "招生", "就业", "活动", "服务", "合作", "交流", "学术", "科研", "学科",
            "组织", "职能", "历史", "沿革", "发展", "规划", "制度", "政策", "通知", "公告",
            "新闻", "会议", "讲座", "招聘", "下载", "字母", "师资", "名录", "人才", "党建",
            "学生", "联系", "关于", "简介", "分享", "搜索", "导航", "退休", "学者", "院士",
            "性别", "姓名", "职务", "学历", "学位", "邮箱", "电话", "地址", "导师", "系所",
            "学习", "挖掘", "隐私", "师德", "正文", "简报", "指南", "办事", "季度", "风采",
            "掠影", "映像", "相册", "视频", "成员", "概况", "链接", "平台", "基地", "系所",
            "详细", "详情", "查看", "点击", "展开", "收起", "上一页", "下一页",
            "自动化系", "计算机系", "中心", "实验室", "重点", "工程", "技术", "科学", "研究",
            "网络", "软件", "安全", "智能", "数据", "图像", "算法", "模型", "视觉", "语音", "芯片", "电路", "通信", "信号", "控制", "机器人", "医学", "生物", "计算", "识别", "感知", "语言", "知识", "图形", "媒体", "正高", "副高", "中级", "高工", "教师节", "迎新", "军训", "招生简章", "国际化", "国际", "交流",
            "合作", "服务", "文化", "活动"]


def normalize_rank(title):
    for rank, words in RANK_MAP:
        for word in words:
            if word in (title or ""):
                return rank
    return "其他"


def clean(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


# 研究方向里混进来的导航/切换文字：削掉前缀，剩下若只是导航词就整段丢弃（不补写）
DIR_NOISE = re.compile(r"^(更多|语种切换|其他栏目|首页|师资队伍|教师名录|列表|导航|登录|关闭|"
                       r"上一篇|下一篇|点击|展开|收起|English|中文)[\s>·`﹥>»-]*")
DIR_NAV_ONLY = re.compile(r"^(其他栏目|语种切换|English|更多|首页|师资队伍|教师名录|列表|导航|中文)"
                          r"[\s>·`]*$")


def clean_direction(value):
    text = clean(value)
    for _ in range(3):
        stripped = DIR_NOISE.sub("", text).strip(" >·`-")
        if stripped == text:
            break
        text = stripped
    # 正文里混进的页脚/导航：在这些标记处截断
    cut = len(text)
    for marker in ("其他栏目", "语种切换", "首页 >", "首页>", "首页 首页", "中文 English", "首页 上页", "上页", "尾页"):
        pos = text.find(marker)
        if 0 <= pos < cut:
            cut = pos
    text = text[:cut].strip(" >·`-")
    if not text or len(text) < 4 or DIR_NAV_ONLY.match(text):
        return ""
    return text


def main():
    load_universities()
    src = os.path.join(WORK, "people_final.json")
    if not os.path.exists(src):
        src = os.path.join(WORK, "people_detail.json")
    people = json.load(open(src, encoding="utf-8"))

    dropped = collections.Counter()
    staged = []
    for p in people:
        name = clean(p.get("name"))
        uni = clean(p.get("university"))
        if not NAME_RE.match(name) or any(b in name for b in BAD_NAME):
            dropped["姓名不合规"] += 1
            continue
        if uni not in UNIVERSITIES:
            dropped["学校不在名单"] += 1
            continue
        title = clean(p.get("title"))
        rank = normalize_rank(title)
        direction = clean_direction(p.get("direction"))
        if rank == "其他" and not direction:
            dropped["无职称且无方向"] += 1
            continue
        staged.append({
            "university": uni,
            "city": UNIVERSITIES[uni]["city"],
            "tags": UNIVERSITIES[uni]["tags"],
            # 优先用该条记录自己的院系（同一所高校可能有多个院系），否则退回学校默认院系
            "school": clean(p.get("school")) or UNIVERSITIES[uni]["school"],
            "name": name,
            "title": title,
            "rank": rank,
            "direction": direction,
            "orcid": clean(p.get("orcid")),
            # 邮箱不对外发布：聚合后的邮箱列表易被滥用，需要时请到来源页面自行核对
            # 没有个人详情页时，来源退回到他所在的师资栏目页
            "source": clean(p.get("source")) or clean(p.get("list_source")),
            "note": clean(p.get("orcid_note")),
        })

    # 姓名横跨多校 → 站点栏目词
    by_name = collections.defaultdict(set)
    for r in staged:
        by_name[r["name"]].add(r["university"])
    junk_names = {n for n, unis in by_name.items() if len(unis) >= 3}

    # 同校内去重
    best = {}
    for r in staged:
        if r["name"] in junk_names:
            dropped["疑似栏目词"] += 1
            continue
        key = (r["university"], r["name"])
        cur = best.get(key)
        if cur is None or score(r) > score(cur):
            best[key] = r
        else:
            dropped["重复姓名"] += 1

    records = sorted(best.values(), key=lambda r: (r["university"], r["rank"], r["name"]))
    for i, r in enumerate(records, 1):
        r["id"] = "F%05d" % i

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "faculty.json"), "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=1)

    rank_counts = collections.Counter(r["rank"] for r in records)
    uni_counts = collections.Counter(r["university"] for r in records)
    meta = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "faculty_count": len(records),
        "university_count": len(uni_counts),
        "with_title": sum(1 for r in records if r["title"]),
        "with_direction": sum(1 for r in records if r["direction"]),
        "with_orcid": sum(1 for r in records if r["orcid"]),
        "rank_counts": dict(rank_counts.most_common()),
        "top_universities": uni_counts.most_common(10),
        "sources": [
            "各校院系官网「师资队伍 / 教师名录」栏目页面（每条附来源链接）",
            "ORCID 公开检索接口（pub.orcid.org），用于按「姓名拼音 + 机构」匹配 ORCID，"
            "并回到 ORCID 记录本体复核姓名与任职单位",
        ],
    }
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)

    with open(os.path.join(OUT, "faculty.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "university", "city", "tags", "school", "name", "title",
                         "rank", "direction", "orcid", "source"])
        for r in records:
            writer.writerow([r["id"], r["university"], r["city"], "/".join(r["tags"]),
                             r["school"], r["name"], r["title"], r["rank"], r["direction"],
                             r["orcid"], r["source"]])

    print("records", len(records))
    print("universities", len(uni_counts))
    print("with title/direction/orcid", meta["with_title"], meta["with_direction"],
          meta["with_orcid"])
    print("ranks", dict(rank_counts.most_common()))
    print("dropped", dict(dropped))


def score(r):
    return sum(bool(r.get(k)) for k in ("title", "direction", "orcid", "source"))


if __name__ == "__main__":
    main()
