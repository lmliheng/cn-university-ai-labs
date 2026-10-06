# cn-university-ai-labs

> 中国 985/211 高校「人工智能 · 计算机 · 电子信息」院系的**教师与研究人员名录** —— 姓名、职称、研究方向、ORCID，逐条附院系官网来源链接，并附一个开箱可用的检索页面。

各校院系的师资信息散落在「师资队伍」「教师名录」「研究团队」等不同栏目里，职称叫法不一、没有统一入口。
这个仓库把它们整理成一份**带来源链接的结构化数据**，并提供一个能按职称、学校层次、地区、研究方向检索的前端。

**仓库的主角是数据**：`data/` 下的 JSON 可以直接被别的程序消费，网页只是它的查看器。

## 数据集

| 文件 | 内容 | 规模 | 说明 |
|---|---|---|---|
| `data/faculty.json` | 教师 / 研究人员 | **3096 条，43 所高校** | 每条带职称、研究方向、ORCID（有则填）与来源页面链接 |
| `data/meta.json` | 计数与采集时间 | — | 供程序对账 |
| `data/faculty.csv` | 上面的 CSV 版 | — | 表格工具直接用（由 `npm run dataset` 生成） |

字段覆盖率（`meta.json`）：职称 **3019/3096**、研究方向 **1679/3096**、ORCID **176/3096**。
职称分布：教授 1327 · 副教授 983 · 讲师 328 · 其他 120 · 副研究员 106 · 助理教授 81 · 研究员 74 · 助理研究员 71 · 助教 6。

### `faculty.json` 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 稳定编号（`F00001`…），便于外部引用 |
| `university` | string | 高校中文名 |
| `city` | string | 城市 |
| `tags` | string[] | `985` / `211` / `双一流`（985 校同时带 211） |
| `school` | string | 院系 / 学部 |
| `name` | string | 姓名 |
| `title` | string | 页面上的职称原文，例如 `准聘副教授`、`特聘研究员` |
| `rank` | string | 归一后的职称档位，用于筛选：`教授` `副教授` `助理教授` `讲师` `研究员` `副研究员` `助理研究员` `助教` `其他` |
| `direction` | string | 研究方向，摘录自详情页「研究方向 / 研究领域 / 研究兴趣」的原文；页面没写就留空 |
| `orcid` | string | ORCID iD，格式 `0000-0000-0000-0000`；没有则留空 |
| `source` | string | **来源页面**，可回查核对；没有个人详情页时回退到所在师资栏目页 |
| `note` | string | 采集备注（例如 ORCID 因同名候选过多未回填） |

### 直接取用

```
https://raw.githubusercontent.com/lmliheng/cn-university-ai-labs/main/data/faculty.json
https://raw.githubusercontent.com/lmliheng/cn-university-ai-labs/main/data/meta.json
https://raw.githubusercontent.com/lmliheng/cn-university-ai-labs/main/data/faculty.csv
```

## 数据是怎么来的，能信到什么程度

分三步，每一步都在 `scripts/crawl/` 里可复现：

1. **姓名 + 职称**：抓取各校院系官网「师资队伍 / 教师名录」栏目页面。列表页通常按职称分栏，或每个教师条目里就写着职称 ——
   两者都只做**原文摘录**，不猜测。`title` 是原文，`rank` 是归一后的档位。
2. **研究方向**：抓教师个人详情页，从「研究方向 / 研究领域 / 研究兴趣」后面截取原文。页面没有这一段就留空。
3. **ORCID**：
   - 来源页面上写了 ORCID 的，直接取（最高可信）；
   - 其余用 [ORCID 官方公开检索接口](https://pub.orcid.org/) 按「姓名拼音 + 机构名」查找：
     姓名按拼音归一后必须**完全等价**（词集合或整名连写一致），机构的英文名也必须对得上，
     最后还会**回到 ORCID 记录本体复核**一次姓名与任职单位。三道都过、且**候选人唯一**才回填；
     命中多个一律留空并在 `note` 里写明。
   - 因此 ORCID 一栏是**辅助线索**，引用、投稿或建联系前请以本人 ORCID 主页为准。

采集脚本会做机械校验：姓名必须是 2~4 个汉字且不是栏目词、学校必须在目标名单内、同校同名去重、
姓名若横跨 3 所以上高校则判定为站点栏目词整条丢弃、至少要有一条实质信息（职称或研究方向）。

## 已知缺口（欢迎补）

- **只有 44/60 所高校有数据**：以下学校本次未抓到 —— 上海大学、北京交通大学、北京工业大学、
  北京师范大学、中国人民大学（部分）、国防科技大学、大连理工大学（教师名录为前端渲染）、
  哈尔滨工业大学、天津大学、暨南大学、郑州大学、华南理工大学、华北电力大学、中国矿业大学(北京)、
  华中科技大学、厦门大学、福州大学、武汉大学计算机学院、浙江大学、清华大学电子工程系
  （站点不可达、纯前端渲染或改版），其余多为一两条误抓。
- **研究方向覆盖 54%**：不少院系只在列表页放姓名和职称，个人页没有单独写「研究方向」。
- **ORCID 覆盖只有 176/3096**：中文院系官网极少标注 ORCID；ORCID 注册表里中文作者记录本来就不多，
  而姓名匹配是按「完全等价 + 机构一致 + 记录复核」三重校验做的，宁可留空也不错配（同名候选多的如 `王伟` 直接放弃）。
- **职称档位**：各校体系不同（长聘 / 准聘 / 特聘 / 预聘），`rank` 只做粗归一，细节看 `title` 原文。
- 数据快照时间见 `meta.json`；之后官网的变动不会自动同步。信息仅供检索参考，报考、套磁或合作前请以院系官网为准。

## 网页查看器

Vue 3 + Vite，零外部请求（系统字体、内联图标）。

```bash
npm install
npm run dev        # 开发
npm run build      # 构建到 dist/（data/ 会被原样拷进去）
node server.js 80  # 生产：只用 Node 内置模块的静态服务，含 SPA 回退
npm run verify     # 用 jsdom 挂载真实构建产物驱动 UI，40+ 项断言
```

功能：两个视图（教师名录卡片流 / 按学校），关键词搜索（姓名、研究方向、学校），
职称、学校层次、地区、指定学校筛选，「只看有 ORCID」开关，排序，深浅色主题，
响应式单列到三列，含空状态、加载骨架与错误重试。

## 目录

```
data/                    数据集（本仓库主角）
scripts/crawl/
  discover.py            从院系首页发现「师资队伍」入口与职称分栏
  build_sources.py       生成采集配置 sources.json
  crawl_lists.py         抓列表页 → 姓名 / 职称 / 详情链接（含翻页）
  render.mjs             用 Playwright 渲染前端渲染型页面（可选，需 playwright）
  enrich_detail.py       抓教师详情页 → 研究方向 / ORCID / 邮箱
  orcid_registry.py      用 ORCID 公开接口按姓名 + 机构回填 ORCID（含记录本体复核）
  extract.py             页面 → 记录的解析规则（姓名 / 职称 / 研究方向）
  fetcher.py             带磁盘缓存、限速的抓取基座
  build_dataset.py       合并 + 校验 + 导出 data/faculty.json / meta.json / csv
src/                     Vue 3 页面
server.js                生产静态服务
test/verify.mjs          jsdom 集成测试
```

### 重建数据

```bash
python3 scripts/crawl/discover.py        # 探测各校师资入口（结果写入 discover.json）
python3 scripts/crawl/build_sources.py   # 生成 sources.json
python3 scripts/crawl/crawl_lists.py     # 抓列表页
python3 scripts/crawl/enrich_detail.py   # 抓详情页补研究方向 / ORCID
python3 scripts/crawl/orcid_registry.py  # ORCID 回填（需要 pypinyin）
python3 scripts/crawl/build_dataset.py   # 校验 + 生成 data/*
npm run build && npm run verify
```

抓取结果按 URL 缓存在 `scripts/crawl/cache/`，重复运行不会重复请求站点。

## 许可

代码 MIT（见 `LICENSE`）。数据为公开的事实性信息（机构名、人名、职称、研究方向）并逐条附来源链接，
仅作检索索引之用；`orcid` 字段来自 ORCID 公开注册表，`faculty.csv/json` 的再分发请一并遵守其条款。
聚合数据可能滞后或有误，不构成报考、求职或合作建议。
若你是相关教师，希望修正或移除某条记录，请开 issue。
