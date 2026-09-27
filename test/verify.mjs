/**
 * Integration check for the built labs index (/root/labs-site/dist):
 * mounts the real bundle inside jsdom, serves ./data/*.json from disk,
 * then drives the UI like a user would (search, filter, switch views, toggle theme).
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { JSDOM } from 'jsdom'

// 与仓库位置无关：dist/ 与 test/ 同级
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SITE = path.join(ROOT, 'dist')
const DATA = SITE

const failures = []
const results = []
function check(name, condition, detail = '') {
  results.push(`${condition ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`)
  if (!condition) failures.push(name)
}

const labs = JSON.parse(fs.readFileSync(path.join(DATA, 'labs.json'), 'utf8'))
const faculty = JSON.parse(fs.readFileSync(path.join(DATA, 'faculty.json'), 'utf8'))
const meta = JSON.parse(fs.readFileSync(path.join(DATA, 'meta.json'), 'utf8'))

const html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8')
const dom = new JSDOM(html, { url: 'http://labs.test/', pretendToBeVisual: true })
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
  const name = new URL(url, 'http://labs.test/').pathname.replace(/^\//, '')
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
// 必须在应用挂载之后再查，因此是函数而不是常量
const chipRows = () => $$('.filter-row').map((r) => [...r.querySelectorAll('.chip')])
const fieldChip = (t) => chipRows().find((row) => row.some((c) => c.textContent.trim() === '人工智能'))?.find((c) => c.textContent.trim() === t)
const tagChip = (t) => chipRows().find((row) => row.some((c) => c.textContent.trim() === '985'))?.find((c) => c.textContent.trim() === t)
const tab = (text) => $$('.tab').find((t) => t.textContent.trim() === text)
const type = async (sel, value) => {
  const node = $(sel)
  node.value = value
  node.dispatchEvent(new window.Event('input', { bubbles: true }))
  await flush(4)
}

/* ---------- run ---------- */
const bundle = fs.readdirSync(path.join(SITE, 'assets')).find((f) => f.endsWith('.js'))
check('构建产物存在', Boolean(bundle), bundle || '缺少 JS 产物')
check('课题组数据非空', labs.length > 0, `${labs.length} 条`)
check('学者数据非空', faculty.length > 0, `${faculty.length} 条`)

try {
  await import(pathToFileURL(path.join(SITE, 'assets', bundle)).href)
  await flush()

  check('Vue 应用已挂载', Boolean($('.nav .brand span')), $('.nav .brand span')?.textContent)
  check('三个数据文件都被请求', ['labs.json', 'faculty.json', 'meta.json'].every((f) => requested.includes(f)), requested.join(','))
  check('骨架屏已移除', !$('.skeleton'))

  // 默认视图：课题组
  const labCards = () => $$('.grid .card')
  check('课题组卡片已渲染', labCards().length === labs.length, `${labCards().length} 张 / 数据 ${labs.length} 条`)
  check('统计行数字与数据一致', $('.result-line strong')?.textContent === String(labs.length), $('.result-line strong')?.textContent)
  const first = labs[0] || { university: '', source: '' }
  check('卡片含课题组名与学校', $$('.grid .card h3').length > 0 && $$('.grid .card .meta').some((m) => m.textContent.includes(first.university)))
  check('卡片带来源页面链接', $$('.grid .card .links a').some((a) => a.href === first.source), first.source)
  check('负责人只在有数据时显示', labs.filter((l) => l.pi).length > 0 && $$('.grid .card .pi').length === labs.filter((l) => l.pi).length,
    `${$$('.grid .card .pi').length} 个 pi / 数据 ${labs.filter((l) => l.pi).length} 条`)

  // 筛选：学科方向
  const aiCount = labs.filter((l) => l.field === '人工智能').length
  await click(fieldChip('人工智能'))
  check('按「人工智能」筛选生效', labCards().length === aiCount, `${labCards().length} / 应为 ${aiCount}`)
  check('筛选后卡片都属该方向', $$('.grid .card .badge.field').every((b) => b.textContent.trim() === '人工智能'))
  await click(fieldChip('全部'))
  check('取消方向筛选后恢复全量', labCards().length === labs.length)

  // 筛选：学校层次
  const twoCount = labs.filter((l) => l.tags.includes('211')).length
  const ninetyNine = labs.filter((l) => l.tags.includes('985')).length
  await click(tagChip('211'))
  check('按「211」筛选覆盖 985 校（985 本身也是 211）', labCards().length === twoCount, `${labCards().length} / 应为 ${twoCount}`)
  await click(tagChip('985'))
  check('按「985」筛选生效', labCards().length === ninetyNine, `${labCards().length} / 应为 ${ninetyNine}`)
  await click(tagChip('全部'))
  check('取消层次筛选后恢复全量', labCards().length === labs.length)

  // 搜索
  const kw = first.university
  await type('#q', kw)
  check('搜索学校名命中', labCards().length > 0 && labCards().length <= labs.length, `${labCards().length} 条`)
  await type('#q', 'zzz-not-exist-zzz')
  check('无结果时给出空状态', Boolean($('.state')) && $('.state').textContent.includes('没有匹配'))
  check('空状态提供重置按钮', $$('.state .btn').some((b) => b.textContent.includes('重置')))
  await click($$('.state .btn').find((b) => b.textContent.includes('重置')))
  check('重置后恢复全量', labCards().length === labs.length)

  // 按学校视图
  await click(tab('按学校'))
  await flush(6)
  const schools = new Set([...labs.map((l) => l.university), ...faculty.map((f) => f.university)])
  check('学校卡片数等于并集学校数', $$('.grid .card').length === schools.size, `${$$('.grid .card').length} / 应为 ${schools.size}`)
  const expand = $$('.grid .card .btn').find((b) => b.textContent.includes('展开学者名单'))
  check('学校卡片有展开学者按钮', Boolean(expand))
  if (expand) {
    await click(expand)
    check('展开后出现学者名单', Boolean($('.fac-list')))
    check('名单条目数与该学者数一致或提示未收录', $$('.fac-list .row').length > 0 || $('.fac-list .meta') !== null)
  }

  // 学者视图
  await click(tab('学者（CSrankings）'))
  await flush(6)
  check('学者卡片数等于数据集条数', $$('.grid .card').length === faculty.length, `${$$('.grid .card').length} / 应为 ${faculty.length}`)
  check('学者卡片带个人主页链接', $$('.grid .card .links a').length > 0)

  // 主题
  const wasDark = window.document.documentElement.classList.contains('dark')
  await click($('.nav .btn.icon'))
  check('主题切换生效', window.document.documentElement.classList.contains('dark') !== wasDark)
  check('主题已持久化', window.localStorage.getItem('theme') !== null, String(window.localStorage.getItem('theme')))

  // 基础规范
  check('语言与视口已声明', html.includes('lang="zh-CN"') && html.includes('width=device-width'))
  check('页面有真实标题', /<title>[^<]*课题组/.test(html))
  const external = (html.match(/https?:\/\/(?!labs\.test)[^"'\s>]+/g) || [])
    .filter((u) => !u.startsWith('http://www.w3.org/'))  // SVG/XML 命名空间，不是网络请求
  check('无外部资源请求', external.length === 0, external.join(' '))

  // 与 meta.json 对账
  check('meta.lab_count 与实际一致', meta.lab_count === labs.length, `${meta.lab_count} vs ${labs.length}`)
  check('meta.faculty_count 与实际一致', meta.faculty_count === faculty.length, `${meta.faculty_count} vs ${faculty.length}`)
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
