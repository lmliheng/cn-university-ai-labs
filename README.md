# cn-university-ai-labs

> 中国 985/211 高校**理工科院系教师与研究人员名录** —— 覆盖数学、物理、化学、材料、机械、能源、计算机、人工智能、电子信息等方向，给出姓名、职称、研究方向、ORCID，逐条附院系官网来源链接，并附一个开箱可用的检索页面。

各校院系的师资信息散落在「师资队伍」「教师名录」「研究团队」等不同栏目里，职称叫法不一、没有统一入口。
这个仓库把它们整理成一份**带来源链接的结构化数据**，并提供一个能按职称、学校层次、地区、研究方向检索的前端。

**仓库的主角是数据**：`data/` 下的 JSON 可以直接被别的程序消费，网页只是它的查看器。

## 数据集

| 文件 | 内容 | 规模 | 说明 |
|---|---|---|---|
| `data/faculty.json` | 教师 / 研究人员 | **5334 条，45 所高校，71 个院系** | 每条带职称、研究方向、ORCID（有则填）与来源页面链接 |
| `data/meta.json` | 计数与采集时间 | — | 供程序对账 |
| `data/faculty.csv` | 上面的 CSV 版 | — | 表格工具直接用（由 `npm run dataset` 生成） |

字段覆盖率（`meta.json`）：职称 **5221/5334**、研究方向 **3286/5334**、ORCID **213/5334**。
职称分布：教授 2229 · 副教授 1644 · 讲师 427 · 副研究员 252 · 研究员 226 · 助理研究员 217 · 其他 209 · 助理教授 122 · 助教 8。

学科方向分布（按院系名归一，页面上可筛选）：计算机 1588 · 人工智能 870 · 电子信息 868 · 数学 511 · 材料 471 · 机械 467 · 物理 257 · 化学 237 · 地球科学 143 · 能源 64。

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

采集脚本会做机械校验：姓名必须是 2~4 个汉字且不在栏目词表（`build_dataset.py` 的 `BAD_NAME`：
学院 / 师资 / 导师 / 专任教师 / 博士后 / 区块链 …）内、学校必须在目标名单内、同校同名去重、
至少要有一条实质信息（职称或研究方向）。

姓名横跨极多所高校的还会被当作站点栏目词丢弃，但阈值设在 **≥6 所**：常见姓名（张伟、王勇、陈伟…）
在几十所高校里本来就会重名，阈值过松会误伤真人，栏目词改由上面的词表点名处理。

## 已知缺口（欢迎补）

- **45/60 所高校有数据，71 个院系**：以下高校本次仍未抓到 —— 上海大学、中国农业大学、
  中国地质大学(武汉)、北京交通大学、北京化工大学、北京理工大学、华北电力大学、华南理工大学、
  厦门大学、国防科技大学、大连理工大学、暨南大学、福州大学、郑州大学（站点不可达、纯前端渲染或改版）。
  另有若干新加的理工科院系列在下方单独说明。
- **研究方向覆盖 62%**：不少院系只在列表页放姓名和职称，个人页没有单独写「研究方向」。
- **ORCID 覆盖只有 213/5334**：中文院系官网极少标注 ORCID；ORCID 注册表里中文作者记录本来就不多，
  而姓名匹配是按「完全等价 + 机构一致 + 记录复核」三重校验做的，宁可留空也不错配（同名候选多的如 `王伟` 直接放弃）。
- **职称档位**：各校体系不同（长聘 / 准聘 / 特聘 / 预聘），`rank` 只做粗归一，细节看 `title` 原文。
- **理工科方向里覆盖偏薄的院系**：上海交通大学数学科学学院、南京大学数学系 / 物理学院 / 化学化工学院、
  复旦大学化学系、东南大学数学学院（师资页为空或不含姓名-职称），中国科学技术大学物理学院（3 条）、
  西安交通大学数学与统计学院（2 条，名录入口只放出少量）。
  中南大学的自动化学院、机械与土木工程学院站点本次**无法访问**（域名不可达 / 403），故未收录。
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

功能：两个视图（教师名录卡片流 / 按学校），关键词搜索（姓名、研究方向、院系、学校），
职称、学校层次、**学科方向**、地区、指定学校筛选，「只看有 ORCID」开关，排序，深浅色主题，
响应式单列到三列，含空状态、加载骨架与错误重试。

## 目录

```
data/                    数据集（本仓库主角）
scripts/crawl/
  discover.py            从院系首页发现「师资队伍」入口与职称分栏
  build_sources.py       生成采集配置 sources.json
  seeds.py               新院系（理工科方向）的院系首页种子清单
  discover_seeds.py      对种子逐校发现师资入口 → discover_seeds.json
  build_sources_seeds.py 把发现的种子并入 sources.json（供新增院系用）
  crawl_batch.py         只抓本批新增院系 → people_batch_raw.json
  crawl_lists.py         抓列表页 → 姓名 / 职称 / 详情链接（含翻页）
  render.mjs             用 Playwright 渲染前端渲染型页面（可选，需 playwright）
  enrich_detail.py       抓教师详情页 → 研究方向 / ORCID / 邮箱
  enrich_batch.py        同上，但只处理本批新增院系 → people_batch_detail.json
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

**新增一批院系（例如这次加的理工科方向）**：

```bash
# 1. 在 scripts/crawl/seeds.py 里补上院系首页 URL
python3 scripts/crawl/discover_seeds.py       # 发现各院系的师资入口与职称分栏
python3 scripts/crawl/build_sources_seeds.py  # 并入 sources.json
python3 scripts/crawl/crawl_batch.py          # 只抓这批新院系
# 若某些页面是 JS 渲染，先渲染再重抓：
#   node scripts/crawl/render.mjs <urls.txt> scripts/crawl/rendered
python3 scripts/crawl/enrich_batch.py         # 补研究方向 / ORCID
# 2. 把 people_batch_detail.json 并入 people_final.json（同校同名去重）
python3 scripts/crawl/build_dataset.py
```

抓取结果按 URL 缓存在 `scripts/crawl/cache/`，重复运行不会重复请求站点。

## 许可

代码 MIT（见 `LICENSE`）。数据为公开的事实性信息（机构名、人名、职称、研究方向）并逐条附来源链接，
仅作检索索引之用；`orcid` 字段来自 ORCID 公开注册表，`faculty.csv/json` 的再分发请一并遵守其条款。
聚合数据可能滞后或有误，不构成报考、求职或合作建议。
若你是相关教师，希望修正或移除某条记录，请开 issue。
