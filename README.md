# cn-university-ai-labs

> 中国 985/211 高校「人工智能 · 计算机 · 电子信息」课题组数据集 —— 附一个开箱可用的检索页面。

各校院系官网的课题组信息散落在「研究团队」「实验室」「科研机构」等不同栏目里，格式各异、没有统一入口。
这个仓库把它们整理成一份**带来源链接的结构化数据**，并提供一个能按学校、学科方向、层次检索的前端。

**仓库的主角是数据**：`data/` 下的 JSON 可以直接被别的程序消费，网页只是它的查看器。

## 数据集

| 文件 | 内容 | 规模 | 说明 |
|---|---|---|---|
| `data/labs.json` | 课题组 / 实验室 / 研究团队 | **295 条，60 所高校** | 每条都带来源页面链接 |
| `data/faculty.json` | 计算机领域学者 | **2750 位，48 所高校** | 来自 CSrankings，全部带个人主页 |
| `data/meta.json` | 计数与采集时间 | — | 供程序对账 |
| `data/*.csv` | 上面两份数据的 CSV 版 | — | 表格工具直接用（由 `scripts/export_csv.py` 生成） |

统计（`meta.json`）：人工智能 142 · 计算机 105 · 电子信息 48；带负责人的条目 173/295，带研究方向的 215/295。

### `labs.json` 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `university` | string | 高校中文名 |
| `city` | string | 城市 |
| `tags` | string[] | `985` / `211` / `双一流`（985 校同时带 211） |
| `school` | string | 院系或研究院 |
| `group` | string | 课题组 / 实验室 / 团队名称 |
| `pi` | string | 负责人（页面未标注时为空） |
| `field` | string | 三选一：`人工智能` `计算机` `电子信息` |
| `direction` | string | 研究方向（页面未列出时为空） |
| `homepage` | string | 课题组主页，没有则为空 |
| `source` | string | **采集来源页面**，可回查核对 |
| `note` | string | 采集备注（来源性质、空缺原因等） |

`faculty.json` 字段：`university`、`city`、`tags`、`name`、`homepage`。

### 直接取用

```
https://raw.githubusercontent.com/lmliheng/cn-university-ai-labs/main/data/labs.json
https://raw.githubusercontent.com/lmliheng/cn-university-ai-labs/main/data/faculty.json
```

## 数据是怎么来的，能信到什么程度

- **课题组**：逐个抓取各校计算机 / 人工智能 / 电子信息学院官网的「研究团队 / 实验室 / 科研机构」栏目页面，
  团队名、负责人、研究方向**逐字来自页面文本**，不做补写；页面没写负责人的条目 `pi` 留空并在 `note` 里说明，不猜测姓名。
  每条都能用 `source` 回到原页面核对。
- **学者**：来自 [CSrankings](https://github.com/emeryberger/CSrankings) 公开数据集，按其主页域名（`*.edu.cn` / `*.ac.cn`）
  筛选中国内地高校。它**只覆盖计算机领域有论文发表记录的教师**，不等于院系全量师资，排序也不代表水平。
- 采集环境对部分站点不可达（WAF 挑战页、超时），这些学校未被收录，**不是这些学校没有课题组**。

## 已知缺口（欢迎补）

- **0 条的高校**：北京邮电大学、南京理工大学、西南交通大学、兰州大学 —— 采集时站点返回 WAF 挑战或超时。
- **负责人覆盖 173/295**：多数学院只发布平台名录、不写负责人。
- **研究方向覆盖 215/295**：来源页只有名称时留空。
- 数据快照时间 **2026-09-28**，之后官网的变动不会自动同步。信息仅供检索参考，报考、套磁或合作前请以院系官网为准。

## 网页查看器

Vue 3 + Vite，零外部请求（系统字体、内联图标）。

```bash
npm install
npm run dev        # 开发
npm run build      # 构建到 dist/（data/ 会被原样拷进去）
node server.js 80  # 生产：只用 Node 内置模块的静态服务，含 SPA 回退
npm run verify     # 用 jsdom 挂载真实构建产物驱动 UI，34 项断言
```

功能：三个视图（课题组卡片流 / 按学校 / 学者），关键词搜索，学科方向、学校层次、地区、指定学校筛选与排序，
深浅色主题，响应式单列到三列，含空状态、加载骨架与错误重试。

## 目录

```
data/                 数据集（本仓库主角）
scripts/merge_labs.py 采集分片 → data/*.json 的合并与校验（丢弃字段非法、缺来源、学校不在名单内的条目）
scripts/export_csv.py 导出 CSV
src/                  Vue 3 页面
server.js             生产静态服务
test/verify.mjs       jsdom 集成测试
```

## 许可

代码 MIT（见 `LICENSE`）。数据为公开的事实性信息（机构名、人名、研究方向）并逐条附来源链接，
仅作检索索引之用；`faculty.json` 源自 [CSrankings](https://github.com/emeryberger/CSrankings)，遵循其 MIT 许可。
若你是相关课题组负责人，希望修正或移除某条记录，请开 issue。
