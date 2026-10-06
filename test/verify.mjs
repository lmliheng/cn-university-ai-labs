/**
 * Integration check for the built faculty index (dist/):
 * mounts the real bundle inside jsdom, serves ./faculty.json + ./meta.json from disk,
 * then drives the UI like a user would (search, filter by 职称/层次/ORCID, switch views, toggle theme).
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { JSDOM } from 'jsdom'

// 与仓库位置无关：dist/ 与 test/ 同级
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SITE = path.join(ROOT, 'dist')

const failures = []
const results = []
function check(name, condition, detail = '') {
  results.push(`${condition ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`)
  if (!condition) failures.push(name)
}

const faculty = JSON.parse(fs.readFileSync(path.join(SITE, 'faculty.json'), 'utf8'))
const meta = JSON.parse(fs.readFileSync(path.join(SITE, 'meta.json'), 'utf8'))

const html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8')
const dom = new JSDOM(html, { url: 'http://faculty.test/', pretendToBeVisual: true })
const { window } = dom

for (const key of [
  'window', 'document', 'navigator', 'localStorage', 'location', 'history',
  'Element', 'Node', 'Text', 'Comment', 'DocumentFragment', 'Document', 'NodeList',
  'HTMLCollection', 'HTMLElement', 'HTMLInputElement', 'HTMLTextAreaElement',
  'HTMLUnknownElement', 'SVGElement', 'MathMLElement', 'CSSStyleDeclaration', 'DOMRect',
  'Event', 'KeyboardEvent', 'InputEvent', 'CustomEvent', 'MutationObserver',
  'requestAnimationFrame', 'cancelAnimationFrame', 'getComputedStyle',
]) {
  try {
    globalThis[key] = window[key]
  } catch {
    Object.defineProperty(globalThis, key, { value: window[key], configurable: true, writable: true })
  }
}
globalThis.matchMedia = window.matchMedia?.bind(window) ?? (() => ({ matches: false, addEventListener() {}, removeEventListener() {} }))

/* ---------- serve ./data/*.json from disk, like the deployed server does ---------- */
const requested = []
globalThis.fetch = async (url) => {
  const name = new URL(url, 'http://faculty.test/').pathname.replace(/^\//, '')
  requested.push(name)
  const file = path.join(SITE, name)
  if (!fs.existsSync(file)) return { ok: false, status: 404, json: async () => ({}) }
  return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(file, 'utf8')) }
}

const flush = async (rounds = 12) => {
  for (let i = 0; i < rounds; i += 1) await new Promise((resolve) => setTimeout(resolve, 0))
}
const $ = (s) => window.document.querySelector(s)
const $$ = (s) => [...window.document.querySelectorAll(s)]
const click = async (node) => { node.click(); await flush(6) }
const chipRows = () => $$('.filter-row').map((r) => [...r.querySelectorAll('.chip')])
const rankChip = (t) => chipRows().find((row) => row.some((c) => c.textContent.trim() === '教授'))?.find((c) => c.textContent.trim() === t)
const tagChip = (t) => chipRows().find((row) => row.some((c) => c.textContent.trim() === '985'))?.find((c) => c.textContent.trim() === t)
const orcidToggle = () => $$('.chip').find((c) => c.textContent.includes('ORCID'))
const tab = (text) => $$('.tab').find((t) => t.textContent.trim() === text)
const cards = () => $$('.grid .card')
const type = async (sel, value) => {
  const node = $(sel)
  node.value = value
  node.dispatchEvent(new window.Event('input', { bubbles: true }))
  await flush(4)
}

/* ---------- 数据自身的完整性 ---------- */
check('教师数据非空', faculty.length > 0, `${faculty.length} 条`)
check('每条记录有姓名与学校', faculty.every((f) => f.name && f.university))
check('每条记录带来源链接', faculty.every((f) => /^https?:\/\//.test(f.source || '')),
  `${faculty.filter((f) => /^https?:\/\//.test(f.source || '')).length}/${faculty.length}`)
check('职称已归一为可筛选值', faculty.every((f) => f.rank && f.rank !== ''))
check('ORCID 格式合法', faculty.filter((f) => f.orcid).every((f) => /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/.test(f.orcid)),
  `${faculty.filter((f) => f.orcid).length} 条有 ORCID`)
check('id 唯一', new Set(faculty.map((f) => f.id)).size === faculty.length)
check('meta 计数与数据一致', meta.faculty_count === faculty.length, `${meta.faculty_count} vs ${faculty.length}`)
check('meta 覆盖字段计数一致',
  meta.with_title === faculty.filter((f) => f.title).length &&
  meta.with_direction === faculty.filter((f) => f.direction).length &&
  meta.with_orcid === faculty.filter((f) => f.orcid).length)

/* ---------- run ---------- */
const bundle = fs.readdirSync(path.join(SITE, 'assets')).find((f) => f.endsWith('.js'))
check('构建产物存在', Boolean(bundle), bundle || '缺少 JS 产物')

try {
  await import(pathToFileURL(path.join(SITE, 'assets', bundle)).href)
  await flush()

  check('Vue 应用已挂载', Boolean($('.nav .brand span')), $('.nav .brand span')?.textContent)
  check('两个数据文件都被请求', ['faculty.json', 'meta.json'].every((f) => requested.includes(f)), requested.join(','))
  check('骨架屏已移除', !$('.skeleton'))

  // 默认视图：教师名录
  check('教师卡片已渲染', cards().length === faculty.length, `${cards().length} 张 / 数据 ${faculty.length} 条`)
  check('统计行数字与数据一致', $('.result-line strong')?.textContent === String(faculty.length), $('.result-line strong')?.textContent)
  const first = faculty[0]
  check('卡片含姓名与学校', $$('.grid .card h3').length > 0 && $$('.grid .card .meta').some((m) => m.textContent.includes(first.university)))
  check('卡片显示职称徽标', cards().filter((c) => c.querySelector('.badge.rank')).length === faculty.length)
  check('卡片带来源页面链接', $$('.grid .card .links a').some((a) => a.href === first.source), first.source)
  const withDir = faculty.filter((f) => f.direction).length
  check('研究方向只在有数据时显示', $$('.grid .card .dir').length === withDir, `${$$('.grid .card .dir').length} / 数据 ${withDir} 条`)
  const withOrcid = faculty.filter((f) => f.orcid).length
  check('ORCID 链接指向 orcid.org', $$('.grid .card .links a.orcid').length === withOrcid &&
    $$('.grid .card .links a.orcid').every((a) => a.href.startsWith('https://orcid.org/')),
    `${$$('.grid .card .links a.orcid').length} / 数据 ${withOrcid} 条`)

  // 筛选：职称
  const profCount = faculty.filter((f) => f.rank === '教授').length
  await click(rankChip('教授'))
  check('按「教授」筛选生效', cards().length === profCount, `${cards().length} / 应为 ${profCount}`)
  check('筛选后都是教授', $$('.grid .card .badge.rank').every((b) => b.textContent.trim() === '教授'))
  await click(rankChip('全部'))
  check('取消职称筛选后恢复全量', cards().length === faculty.length)

  // 筛选：只看有 ORCID
  await click(orcidToggle())
  check('「只看有 ORCID」筛选生效', cards().length === withOrcid, `${cards().length} / 应为 ${withOrcid}`)
  await click(orcidToggle())
  check('取消 ORCID 筛选后恢复全量', cards().length === faculty.length)

  // 筛选：学校层次
  const tag211 = faculty.filter((f) => (f.tags || []).includes('211')).length
  const tag985 = faculty.filter((f) => (f.tags || []).includes('985')).length
  await click(tagChip('211'))
  check('按「211」筛选覆盖 985 校（985 本身也是 211）', cards().length === tag211, `${cards().length} / 应为 ${tag211}`)
  await click(tagChip('985'))
  check('按「985」筛选生效', cards().length === tag985, `${cards().length} / 应为 ${tag985}`)
  await click(tagChip('全部'))
  check('取消层次筛选后恢复全量', cards().length === faculty.length)

  // 搜索
  await type('#q', first.university)
  check('搜索学校名命中', cards().length > 0 && cards().length <= faculty.length, `${cards().length} 条`)
  const dirSample = faculty.find((f) => f.direction && f.direction.length > 4)
  if (dirSample) {
    await type('#q', dirSample.direction.slice(0, 6))
    check('搜索研究方向命中', cards().length > 0, `关键词「${dirSample.direction.slice(0, 6)}」→ ${cards().length} 条`)
  }
  await type('#q', 'zzz-not-exist-zzz')
  check('无结果时给出空状态', Boolean($('.state')) && $('.state').textContent.includes('没有匹配'))
  check('空状态提供重置按钮', $$('.state .btn').some((b) => b.textContent.includes('重置')))
  await click($$('.state .btn').find((b) => b.textContent.includes('重置')))
  check('重置后恢复全量', cards().length === faculty.length)

  // 筛选：学科方向（理工科院系）
  const discChip = (t) => chipRows().find((row) => row.some((c) => c.textContent.trim() === '数学'))
    ?.find((c) => c.textContent.trim() === t)
  const mathChip = discChip('数学')
  check('提供「学科方向」筛选', Boolean(mathChip && chipRows().some((r) => r.some((c) => c.textContent.trim() === '物理'))))
  if (mathChip) {
    await click(mathChip)
    const n = cards().length
    check('按「数学」学科筛选生效', n > 0 && n < faculty.length, `${n} 条`)
    check('筛选结果都属于数学类院系',
      $$('.grid .card .meta').every((m) => /数学|统计/.test(m.textContent)), `${n} 张卡片`)
    await click(discChip('全部'))
    check('取消学科筛选后恢复全量', cards().length === faculty.length)
  }

  // 按学校视图
  await click(tab('按学校'))
  await flush(6)
  const schools = new Set(faculty.map((f) => f.university))
  check('学校卡片数等于学校数', cards().length === schools.size, `${cards().length} / 应为 ${schools.size}`)
  const expand = $$('.grid .card .btn').find((b) => b.textContent.includes('展开名单'))
  check('学校卡片有展开名单按钮', Boolean(expand))
  if (expand) {
    await click(expand)
    check('展开后出现教师名单', Boolean($('.fac-list')) && $$('.fac-list .row').length > 0,
      `${$$('.fac-list .row').length} 条`)
    check('名单里带职称', $$('.fac-list .row b').length === $$('.fac-list .row').length)
  }

  // 主题
  const wasDark = window.document.documentElement.classList.contains('dark')
  await click($('.nav .btn.icon'))
  check('主题切换生效', window.document.documentElement.classList.contains('dark') !== wasDark)
  check('主题已持久化', window.localStorage.getItem('theme') !== null, String(window.localStorage.getItem('theme')))

  // 基础规范
  check('语言与视口已声明', html.includes('lang="zh-CN"') && html.includes('width=device-width'))
  check('页面有真实标题', /<title>[^<]*教师/.test(html), html.match(/<title>([^<]*)</)?.[1])
  const external = (html.match(/https?:\/\/(?!faculty\.test)[^"'\s>]+/g) || [])
    .filter((u) => !u.startsWith('http://www.w3.org/'))  // SVG/XML 命名空间，不是网络请求
  check('无外部资源请求', external.length === 0, external.join(' '))
} catch (error) {
  failures.push(`运行时异常：${error.message}`)
  results.push(`FAIL  运行时异常：${error.stack}`)
}

console.log(results.join('\n'))
console.log(`\n${results.filter((l) => l.startsWith('PASS')).length} 项通过，${failures.length} 项失败`)
if (failures.length) {
  console.log('失败项：' + failures.join(' | '))
  process.exit(1)
}
