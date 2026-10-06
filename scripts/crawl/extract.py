"""从师资列表页 / 详情页里抽取教师记录。

通用策略：按块级容器（li / tr）切块，块内找「姓名 + 职称 + 研究方向」。
只做摘录，不做补写：找不到的字段留空。
"""
import html as htmllib
import re

RANK_RE = re.compile(
    r"(特聘教授|特聘研究员|特聘副研究员|准聘副教授|准聘助理教授|预聘助理教授|长聘教授|助理研究员|"
    r"副教授|副研究员|助理教授|教授|研究员|讲师|助教|高级工程师|教授级高工|工程师|实验师|主任医师)"
)

ORCID_RE = re.compile(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b")

DIR_KEYS = ["主要研究方向", "研究方向与兴趣", "主要研究领域", "主要研究兴趣", "主要研究内容",
            "研究方向", "研究领域", "研究兴趣", "科研方向", "学科方向", "主要方向", "研究内容",
            "招生方向"]

# 研究方向文本的截断词：下一个栏目标题或明显不属于方向的段落
CUT_WORDS = ["论文发表", "获奖情况", "学术成果", "教育背景", "教学工作", "主要论著", "个人简介",
             "联系方式", "科研项目", "主持", "参与", "招生信息", "社会兼职", "荣誉", "专利",
             "项目", "讲授", "课程", "代表", "获奖", "工作经历", "研究方向", "研究领域",
             "研究兴趣", "科研方向", "承担", "出版", "著作", "邮箱", "电话", "地址",
             "联系", "版权所有", "上一篇", "下一篇", "兴趣爱好", "主要成果", "教育经历",
             "个人主页", "主要论文", "代表论文", "科研概况", "个人履历", "工作单位",
             "导师类别", "暂无内容", "主讲", "团队成员", "曾任", "现任", "学位", "教育及",
             "科研成果", "学生工作", "科研团队", "获奖信息", "基本情况",
             "办公", "通讯", "论文成果", "实验室主页", "导师类型", "导师特点", "在研",
             "目前", "主页", "副教授", "教授", "讲师", "研究员", "职称", "学位"]

CONNECTORS = ["主要包括", "包括", "主要为", "主要是", "为", "是", "有"]


def extract_direction(text):
    """从一段文本里摘出「研究方向」原文（不补写，只截取）。"""
    for key in DIR_KEYS:
        for m in re.finditer(re.escape(key), text):
            tail = text[m.end():m.end() + 300]
            tail = re.sub(r"^[\s:：,，、\-—]*", "", tail)
            for conn in CONNECTORS:
                if tail.startswith(conn):
                    tail = tail[len(conn):]
                    tail = re.sub(r"^[\s:：,，、\-—]*", "", tail)
                    break
            cut = len(tail)
            for stop in CUT_WORDS:
                pos = tail.find(stop)
                if 0 <= pos < cut:
                    cut = pos
            for stop in ("。", "；", ";", "\n"):
                pos = tail.find(stop)
                if 0 < pos < cut:
                    cut = pos
            val = tail[:cut]
            val = re.sub(r"<[^>]*>?", " ", val)
            val = re.sub(r"\s+", " ", val).strip(" 　；;。,，")
            if 4 <= len(val) <= 200:
                return val
    return ""

TITLE_LINE_RE = re.compile(r"^\s*(职称|职务|岗位|头衔)\s*[:：]?\s*(.{0,20})$")

# 不是人名的常见词
STOP_NAMES = set("""
首页 上页 下页 尾页 末页 更多 学院 大学 学校 中心 实验室 研究所 研究院 团队 教师 学生 校友
党建 工会 新闻 通知 公告 招聘 概况 简介 队伍 人员 老师 导师 教授 副教授 讲师 研究员 助教
姓名 职称 序号 主页 邮箱 电话 地址 邮编 传真 联系 我们 关于 返回 登录 注册 搜索 检索 全部
组织 机构 历史 沿革 现任 领导 概况 学科 科研 教学 人才 培养 招生 就业 国际 交流 合作 服务
社会 文化 学生 活动 基金 下载 专区 链接 友情 版权 所有 权利 保留 技术 支持 备案 号 官方
团队 课题 项目 成果 论文 专利 获奖 荣誉 竞赛 实验 实践 创新 创业 基地 平台 数据 科学 工程
智能 计算 信息 网络 软件 系统 安全 通信 电子 自动化 控制 机械 材料 能源 环境 医学 生物
""".split())

BAD_SUBSTR = ["学院", "大学", "中心", "实验", "研究所", "研究院", "团队", "系所", "学部",
              "委员会", "办公室", "支部", "党委", "工会", "校友", "基金", "基地", "平台",
              "首页", "更多", "名单", "队伍", "导师", "职称", "教授", "简历", "主页",
              "领导", "设置", "建设", "概况", "链接", "公示", "办公", "系统", "邮箱", "门户",
              "部门", "机构", "学会", "协会", "项目", "课程", "教学", "成果", "动态", "快讯",
              "方向", "培养", "招生", "就业", "活动", "服务", "合作", "交流", "学术", "科研",
              "学科", "组织", "职能", "历史", "沿革", "发展", "规划", "制度", "政策", "通知",
              "公告", "新闻", "会议", "讲座", "招聘", "下载", "字母", "师资", "名录", "队伍",
              "人才", "党建", "学生", "联系", "关于", "概况", "简介", "分享", "搜索", "导航",
              "退休", "学者", "院士", "教学", "科学", "工程", "技术", "研究", "信息", "图书",
              "学习", "挖掘", "隐私", "师德", "正文", "简报", "指南", "办事", "季度", "风采",
              "掠影", "映像", "相册", "视频", "成员", "重点",
              "详细", "详情", "查看", "点击", "展开", "收起", "上一页", "下一页",
              "网络", "软件", "安全", "智能", "数据", "图像", "算法", "模型", "视觉", "语音", "芯片", "电路", "通信", "信号", "控制", "机器人", "医学", "生物", "计算", "识别", "感知", "语言", "知识", "图形", "媒体", "正高", "副高", "中级", "高工", "教师节", "迎新", "军训", "招生简章"]

NAME_RE = re.compile(r"^[\u4e00-\u9fa5·]{2,4}$")


def strip_tags(fragment):
    fragment = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"(?i)</(p|div|li|tr|h\d|section|span|strong|b|em|font)>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    fragment = htmllib.unescape(fragment)
    lines = [re.sub(r"[ \t\u3000\xa0]+", " ", ln).strip() for ln in fragment.split("\n")]
    return [ln for ln in lines if ln]


CHROME_TAGS = ("nav", "header", "footer", "aside")
CHROME_ATTR = re.compile(
    r"(?i)\b(?:id|class)\s*=\s*[\"'][^\"']*"
    r"(nav|menu|daohang|header|head-|topbar|top-bar|footer|foot|copyright|crumb|breadcrumb|"
    r"sidebar|side-bar|banner|search|sousuo|logo|bqsy|banquan|link|yqlj|friend)"
    r"[^\"']*[\"']"
)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "param", "source", "track", "wbr"}


def _remove_element(html, start, tag):
    """删除 start 处的 <tag ...> 到其配对 </tag>；找不到配对时只去掉开标签。"""
    depth = 0
    i = start
    open_re = re.compile(r"(?is)<(/?)%s\b[^>]*>" % re.escape(tag))
    while True:
        m = open_re.search(html, i)
        if not m:
            end = html.find(">", start)
            return html[:start] + html[end + 1:] if end >= 0 else html
        end = m.end()
        if m.group(1) == "/":
            depth -= 1
            if depth <= 0:
                return html[:start] + html[end:]
        else:
            depth += 1
        i = end


def strip_chrome(html):
    """去掉站点导航 / 页眉页脚，避免菜单项被当成教师名。"""
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    original = len(html)
    for tag in CHROME_TAGS:
        while True:
            m = re.search(r"(?is)<%s\b[^>]*>" % tag, html)
            if not m:
                break
            trimmed = _remove_element(html, m.start(), tag)
            if len(trimmed) < original * 0.4:
                html = html[:m.start()] + html[html.find(">", m.start()) + 1:]
                break
            html = trimmed
    for _ in range(60):
        m = CHROME_ATTR.search(html)
        if not m:
            break
        pos = html.rfind("<", 0, m.start())
        if pos < 0:
            break
        tm = re.match(r"(?is)<([a-zA-Z][\w:-]*)", html[pos:])
        if not tm:
            break
        tag = tm.group(1).lower()
        if tag in VOID_TAGS:
            html = html[:pos] + html[html.find(">", m.end()) + 1:]
            continue
        # 删掉整页 60% 以上内容说明命中了外层容器，放弃这次删除
        trimmed = _remove_element(html, pos, tag)
        if len(trimmed) < original * 0.4:
            html = html[:pos] + " " + html[html.find(">", m.end()) + 1:]
            continue
        html = trimmed
    return html


def split_blocks(html):
    """按 li / tr / 重复 class 容器切块。"""
    body = strip_chrome(html)
    blocks = re.split(r"(?i)<li\b", body)
    if len(blocks) >= 4:
        return blocks
    blocks = re.split(r"(?i)<tr\b", body)
    if len(blocks) >= 4:
        return blocks
    return [body]


CLASS_RE = re.compile(r'(?i)<(?:div|section|article|ul)\b[^>]*class\s*=\s*["\']([^"\']+)["\']')
STOP_CLASS = re.compile(r"(?i)nav|menu|head|foot|crumb|banner|search|logo|link|side|top|bottom")


def class_blocks(html):
    """按出现次数最多的「卡片 class」切块，适配 div 排版的名单。"""
    body = strip_chrome(html)
    counts = {}
    for m in CLASS_RE.finditer(body):
        for cls in m.group(1).split():
            if STOP_CLASS.search(cls):
                continue
            counts[cls] = counts.get(cls, 0) + 1
    best, best_len = None, 10 ** 9
    for cls, n in counts.items():
        if n < 4:
            continue
        parts = re.split(r'(?i)<[a-z]+\b[^>]*class\s*=\s*["\'][^"\']*\b%s\b[^"\']*["\']' % re.escape(cls), body)
        parts = [p for p in parts if len(p) > 40]
        if len(parts) < 4:
            continue
        lens = sorted(len(p) for p in parts)
        med = lens[len(lens) // 2]
        if med < best_len:
            best, best_len = parts, med
    return best


def line_window_blocks(html):
    """纯文本名单：按行滑窗，每行起一个块。"""
    body = strip_chrome(html)
    lines = strip_tags(body)
    return ["\n".join(lines[i:i + 3]) for i in range(len(lines))]


def first_href(block, base_url):
    m = re.search(r'(?i)<a\b[^>]*href\s*=\s*["\']([^"\']+)["\']', block)
    if not m:
        return ""
    href = m.group(1).strip()
    if href.lower().startswith(("javascript:", "#", "mailto:")):
        return ""
    import urllib.parse
    return urllib.parse.urljoin(base_url, href)


def clean_name(raw):
    name = raw.strip(" 　\t·*()（）[]【】")
    name = re.sub(r"\s+", "", name)
    if not NAME_RE.match(name):
        return ""
    if name in STOP_NAMES:
        return ""
    if any(bad in name for bad in BAD_SUBSTR):
        return ""
    return name


def extract_direction_old(text):
    """旧实现（保留作对照）。"""
    for key in DIR_KEYS:
        for m in re.finditer(re.escape(key) + r"\s*[:：]\s*(.{2,240})", text):
            val = m.group(1).strip()
            val = re.split(r"(?:招生|研究方向|研究领域|研究兴趣|科研方向|联系|邮箱|电话|主要成果)\s*[:：]", val)[0]
            val = re.sub(r"\s+", " ", val).strip(" ；;。,")
            if 3 <= len(val) <= 200:
                return val
    return ""


def parse_person_block(block, base_url, hint=""):
    """从一个块里解析一条记录，返回 dict 或 None。"""
    lines = strip_tags(block)
    if not lines:
        return None
    joined = " ".join(lines)
    if len(joined) > 4000:
        return None

    # 姓名：优先块里第一段/第一个链接文本，其次「姓名 + 分隔符 + 其它」的行
    name = ""
    m = re.search(r'(?is)<a\b[^>]*title\s*=\s*["\']([^"\']{2,12})["\']', block)
    if m:
        name = clean_name(m.group(1))
    if not name:
        for line in lines[:6]:
            cand = clean_name(line)
            if cand:
                name = cand
                break
    if not name:
        for line in lines[:6]:
            lm = re.match(r"^([\u4e00-\u9fa5·]{2,4})[\s（()【】、,，:：|－—-]", line)
            if lm:
                cand = clean_name(lm.group(1))
                if cand:
                    name = cand
                    break
    if not name:
        return None

    title = ""
    tm = RANK_RE.search(joined)
    title_explicit = False
    if tm:
        title = tm.group(1)
        title_explicit = True
    if not title and hint:
        tm = RANK_RE.search(hint)
        if tm:
            title = tm.group(1)

    direction = extract_direction(joined)
    orcid = ""
    om = ORCID_RE.search(joined)
    if om:
        orcid = om.group(1)
    email = ""
    em = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", joined)
    if em and "example" not in em.group(0):
        email = em.group(0)

    return {
        "name": name,
        "title": title,
        "title_explicit": title_explicit,
        "direction": direction,
        "orcid": orcid,
        "email": email,
        "source": first_href(block, base_url),
    }


def looks_like_teacher(rec, base_url):
    """过滤站点导航残留：真教师条目通常有职称原文、详情页 id，或站外个人主页。"""
    if rec["title_explicit"] or rec["direction"] or rec["email"]:
        return True
    src = rec["source"]
    if not src:
        return False
    import urllib.parse
    a, b = urllib.parse.urlparse(src), urllib.parse.urlparse(base_url)
    if a.netloc and a.netloc != b.netloc:
        return True
    return bool(re.search(r"\d{3,}", a.path))


def extract_people(html, base_url, hint=""):
    """试多种分块策略，取产出最多的一种。"""
    strategies = [("li", split_blocks(html)), ("cls", class_blocks(html)),
                  ("line", line_window_blocks(html))]
    best, best_n = [], 0
    for _, blocks in strategies:
        if not blocks:
            continue
        out, seen = [], set()
        for block in blocks:
            rec = parse_person_block(block, base_url, hint)
            if not rec or rec["name"] in seen:
                continue
            if not looks_like_teacher(rec, base_url):
                continue
            seen.add(rec["name"])
            out.append(rec)
        if len(out) > best_n:
            best, best_n = out, len(out)
    return best


def extract_by_anchors(html, base_url, hint=""):
    """兜底：把指向详情页的「人名链接」当成一条记录。

    适用于不以 li/tr 排版、或列表由脚本拼装的站点。
    """
    import urllib.parse
    body = strip_chrome(html)
    base = urllib.parse.urlparse(base_url)
    out, seen = [], set()
    pat = re.compile(r'(?is)<a\b([^>]*)>(.*?)</a>')
    for m in pat.finditer(body):
        attrs, inner = m.group(1), m.group(2)
        href_m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', attrs)
        if not href_m:
            continue
        href = href_m.group(1).strip()
        if href.lower().startswith(("javascript:", "#", "mailto:")):
            continue
        url = urllib.parse.urljoin(base_url, href)
        text = re.sub(r"\s+", "", re.sub(r"(?s)<[^>]+>", "", inner))
        name = clean_name(text)
        if not name:
            t = re.search(r'title\s*=\s*["\']([^"\']{2,12})["\']', attrs)
            name = clean_name(t.group(1)) if t else ""
        if not name or name in seen:
            continue
        pu = urllib.parse.urlparse(url)
        last = pu.path.rstrip("/").split("/")[-1] if pu.path else ""
        is_slug = bool(re.match(r"^[A-Za-z][\w.-]*\.(html?|htm|jsp|aspx|php)$", last)) and \
            last.lower() not in ("list.htm", "index.htm", "index.html", "main.htm",
                                 "default.htm", "index_1.htm", "index_2.htm")
        if not (is_slug or re.search(r"\d{3,}", pu.path)
                or (pu.netloc and pu.netloc != base.netloc)):
            continue
        ctx = re.sub(r"(?s)<[^>]+>", " ", body[max(0, m.start() - 400):m.end() + 400])
        ctx = re.sub(r"\s+", " ", htmllib.unescape(ctx))
        title = ""
        tm = RANK_RE.search(ctx)
        if tm:
            title = tm.group(1)
        if not title and hint:
            tm = RANK_RE.search(hint)
            if tm:
                title = tm.group(1)
        seen.add(name)
        out.append({
            "name": name,
            "title": title,
            "title_explicit": bool(title and RANK_RE.search(ctx)),
            "direction": extract_direction(ctx),
            "orcid": (ORCID_RE.search(ctx) or [None, ""])[1] if ORCID_RE.search(ctx) else "",
            "email": "",
            "source": url,
        })
    return out


def extract_best(html, base_url, hint=""):
    """块解析为主，结果太少时用链接兜底。"""
    people = extract_people(html, base_url, hint)
    if len(people) >= 3:
        return people
    alt = extract_by_anchors(html, base_url, hint)
    if len(alt) > len(people):
        return alt
    return people
