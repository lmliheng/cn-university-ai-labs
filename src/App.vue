<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const view = ref('faculty')        // faculty | schools
const query = ref('')
const rank = ref('全部')
const tag = ref('全部')
const discipline = ref('全部')
const region = ref('全部')
const school = ref('全部')
const sortBy = ref('学校')
const onlyOrcid = ref(false)
const openSchool = ref(null)

const faculty = ref([])
const meta = ref(null)
const status = ref('loading')      // loading | ready | error
const errorMsg = ref('')

const RANKS = ['全部', '教授', '副教授', '助理教授', '讲师', '研究员', '副研究员']
const TAGS = ['全部', '985', '211', '双一流']
const SORTS = ['学校', '职称', '姓名']
const DISCIPLINE_ORDER = ['人工智能', '计算机', '电子信息', '自动化', '数学', '物理', '化学',
                          '材料', '机械', '能源', '地球科学', '土木建筑', '生物医学', '其他理工']

// 按院系名称归入学科方向（顺序即优先级）
const DISCIPLINE_RULES = [
  // 「地球科学与信息物理学院」含「信息」，须排在电子信息之前
  ['地球科学', /地球|地质|地理|遥感|测绘/],
  ['人工智能', /人工智能|智能/],
  ['计算机', /计算机|软件|计算/],
  ['电子信息', /电子|信息|通信|集成电路|微电子|光学工程/],
  ['自动化', /自动化|控制|机器人/],
  ['数学', /数学|统计/],
  ['物理', /物理|天文|光学/],
  ['化学', /化学|化工/],
  ['材料', /材料/],
  ['机械', /机械|动力|机电|航空|航天|力学/],
  ['能源', /能源|电气|核|动力工程/],
  ['土木建筑', /土木|建筑|交通|水利|环境/],
  ['生物医学', /生物|医学|生命|药学/]
]
function disciplineOf(f) {
  const text = f.school || ''
  for (const [name, re] of DISCIPLINE_RULES) if (re.test(text)) return name
  return '其他理工'
}

const REGION_MAP = {
  北京: '北京', 天津: '天津', 上海: '上海',
  南京: '江苏', 苏州: '江苏', 无锡: '江苏', 徐州: '江苏',
  杭州: '浙江', 合肥: '安徽',
  武汉: '湖北', 长沙: '湖南', 广州: '广东', 深圳: '广东', 厦门: '福建', 福州: '福建',
  郑州: '河南', 成都: '四川', 重庆: '重庆',
  西安: '陕西', 兰州: '甘肃', 哈尔滨: '黑龙江', 长春: '吉林', 大连: '辽宁', 沈阳: '辽宁',
  济南: '山东', 青岛: '山东', 昆明: '云南', 乌鲁木齐: '新疆', 南昌: '江西'
}

const normalize = (s) => (s || '').toLowerCase()

const allSchools = computed(() => {
  const map = new Map()
  for (const f of faculty.value) {
    if (!map.has(f.university)) {
      map.set(f.university, { name: f.university, city: f.city, tags: f.tags || [], count: 0, orcid: 0, byRank: {}, discs: new Set() })
    }
    const s = map.get(f.university)
    s.count++
    if (f.orcid) s.orcid++
    s.discs.add(disciplineOf(f))
    s.byRank[f.rank] = (s.byRank[f.rank] || 0) + 1
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
})

const disciplines = computed(() => {
  const present = new Set(faculty.value.map(disciplineOf))
  return ['全部', ...DISCIPLINE_ORDER.filter((d) => present.has(d))]
})

const regions = computed(() => {
  const set = new Set()
  for (const s of allSchools.value) set.add(REGION_MAP[s.city] || '其他')
  return ['全部', ...[...set].sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))]
})

const schoolOptions = computed(() => {
  const list = allSchools.value
    .filter((s) => region.value === '全部' || (REGION_MAP[s.city] || '其他') === region.value)
    .filter((s) => tag.value === '全部' || (s.tags || []).includes(tag.value))
    .map((s) => s.name)
  return ['全部', ...list]
})

function matchesCommon(item) {
  if (tag.value !== '全部' && !(item.tags || []).includes(tag.value)) return false
  if (discipline.value !== '全部' && disciplineOf(item) !== discipline.value) return false
  if (region.value !== '全部' && (REGION_MAP[item.city] || '其他') !== region.value) return false
  if (school.value !== '全部' && item.university !== school.value) return false
  return true
}

const filteredFaculty = computed(() => {
  const q = normalize(query.value).trim()
  let list = faculty.value.filter((f) => {
    if (!matchesCommon(f)) return false
    if (rank.value !== '全部' && f.rank !== rank.value) return false
    if (onlyOrcid.value && !f.orcid) return false
    if (!q) return true
    return [f.name, f.title, f.direction, f.university, f.school, f.orcid]
      .some((v) => normalize(v).includes(q))
  })
  const collator = new Intl.Collator('zh-Hans-CN')
  const key = { 学校: (a, b) => collator.compare(a.university, b.university) || collator.compare(a.name, b.name),
                职称: (a, b) => collator.compare(a.rank, b.rank) || collator.compare(a.name, b.name),
                姓名: (a, b) => collator.compare(a.name, b.name) }[sortBy.value]
  return [...list].sort(key)
})

const filteredSchools = computed(() => {
  const q = normalize(query.value).trim()
  return allSchools.value
    .filter((s) => tag.value === '全部' || (s.tags || []).includes(tag.value))
    .filter((s) => region.value === '全部' || (REGION_MAP[s.city] || '其他') === region.value)
    .filter((s) => rank.value === '全部' || (s.byRank[rank.value] || 0) > 0)
    .filter((s) => discipline.value === '全部' || s.discs.has(discipline.value))
    .filter((s) => school.value === '全部' || s.name === school.value)
    .filter((s) => !q || normalize(s.name).includes(q) || normalize(s.city).includes(q))
})

const peopleOf = (name) => faculty.value.filter((f) => f.university === name).slice(0, 400)

function reset() {
  query.value = ''
  rank.value = '全部'
  tag.value = '全部'
  discipline.value = '全部'
  region.value = '全部'
  school.value = '全部'
  sortBy.value = '学校'
  onlyOrcid.value = false
}

watch(region, () => {
  if (school.value !== '全部' && !schoolOptions.value.includes(school.value)) school.value = '全部'
})

const isDark = ref(typeof document !== 'undefined' && document.documentElement.classList.contains('dark'))
function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  try { localStorage.setItem('theme', isDark.value ? 'dark' : 'light') } catch (e) {}
}

async function load() {
  status.value = 'loading'
  errorMsg.value = ''
  try {
    const [f, m] = await Promise.all([
      fetch('./faculty.json').then((r) => { if (!r.ok) throw new Error('faculty.json ' + r.status); return r.json() }),
      fetch('./meta.json').then((r) => { if (!r.ok) throw new Error('meta.json ' + r.status); return r.json() })
    ])
    faculty.value = f
    meta.value = m
    status.value = 'ready'
  } catch (e) {
    status.value = 'error'
    errorMsg.value = e.message || String(e)
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (openSchool.value) openSchool.value = null
    else if (query.value) query.value = ''
  }
}

onMounted(() => { load(); window.addEventListener('keydown', onKeydown) })
</script>

<template>
  <header class="nav">
    <div class="brand">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
        <circle cx="12" cy="8" r="3.2" /><path d="M5 20c0-3.3 3.1-5.6 7-5.6s7 2.3 7 5.6" />
      </svg>
      <span>高校教师索引</span>
    </div>
    <div class="spacer"></div>
    <span class="nav-stats" v-if="status === 'ready'">
      {{ allSchools.length }} 所高校 · {{ faculty.length }} 位教师 · {{ meta?.with_orcid || 0 }} 位有 ORCID
    </span>
    <button class="btn icon" type="button" @click="toggleTheme" :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'">
      <svg v-if="isDark" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" />
      </svg>
    </button>
  </header>

  <main class="wrap">
    <section class="hero">
      <div class="eyebrow">985 / 211 · 数学 · 物理 · 化学 · 材料 · 机械 · 能源 · 计算机 · 电子信息</div>
      <h1>把散落在各校官网的<em>理工科教师与研究人员</em>，收进一个可检索的名录</h1>
      <p>
        覆盖数学、物理、化学、材料、机械、能源、计算机、电子信息等理工科院系。
        每条记录包含姓名、职称、研究方向与 ORCID，并附上院系官网的来源页面链接。
        数据来自各校院系官网「师资队伍」栏目；ORCID 由 ORCID 公开接口按「姓名 + 机构」匹配，并回到 ORCID 记录本体复核。
        信息会随官网变动，报考、套磁或合作前请以院系官网为准。
      </p>
    </section>

    <section class="filters" aria-label="筛选条件">
      <div class="filter-row">
        <label class="sr-only" for="q">搜索</label>
        <input id="q" class="search" v-model="query" type="search"
               placeholder="搜姓名、研究方向或学校，例如「计算机视觉」「张伟」" />
        <button class="btn small" type="button" @click="reset">重置</button>
      </div>

      <div class="filter-row">
        <label>职称</label>
        <button v-for="r in RANKS" :key="r" class="chip" type="button"
                :aria-pressed="rank === r" @click="rank = r">{{ r }}</button>
      </div>

      <div class="filter-row">
        <label>学校层次</label>
        <button v-for="t in TAGS" :key="t" class="chip" type="button"
                :aria-pressed="tag === t" @click="tag = t">{{ t }}</button>
      </div>

      <div class="filter-row">
        <label>学科方向</label>
        <button v-for="d in disciplines" :key="d" class="chip" type="button"
                :aria-pressed="discipline === d" @click="discipline = d">{{ d }}</button>
      </div>

      <div class="filter-row">
        <label for="region">地区</label>
        <select id="region" v-model="region">
          <option v-for="r in regions" :key="r" :value="r">{{ r }}</option>
        </select>
        <label for="school">学校</label>
        <select id="school" v-model="school">
          <option v-for="s in schoolOptions" :key="s" :value="s">{{ s }}</option>
        </select>
        <label for="sort">排序</label>
        <select id="sort" v-model="sortBy">
          <option v-for="s in SORTS" :key="s" :value="s">{{ s }}</option>
        </select>
        <button class="chip" type="button" :aria-pressed="onlyOrcid" @click="onlyOrcid = !onlyOrcid">
          只看有 ORCID
        </button>
      </div>
    </section>

    <div class="tabs" role="tablist" aria-label="视图">
      <button class="tab" role="tab" :aria-selected="view === 'faculty'" @click="view = 'faculty'">教师名录</button>
      <button class="tab" role="tab" :aria-selected="view === 'schools'" @click="view = 'schools'">按学校</button>
    </div>

    <div v-if="status === 'loading'" class="grid" aria-busy="true">
      <div v-for="n in 6" :key="n" class="skeleton">
        <div class="sk-line w60"></div><div class="sk-line w80"></div><div class="sk-line w40"></div>
      </div>
    </div>

    <div v-else-if="status === 'error'" class="state error" role="alert">
      <h3>数据加载失败</h3>
      <p>{{ errorMsg }}</p>
      <button class="btn small" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <!-- 教师名录 -->
      <template v-if="view === 'faculty'">
        <div class="result-line">
          <strong>{{ filteredFaculty.length }}</strong> 位教师
          <span>· 覆盖 {{ new Set(filteredFaculty.map((f) => f.university)).size }} 所高校</span>
          <span v-if="onlyOrcid">· 仅显示有 ORCID 的记录</span>
        </div>
        <div v-if="filteredFaculty.length" class="grid">
          <article v-for="f in filteredFaculty" :key="f.id" class="card teacher">
            <div class="name-row">
              <h3>{{ f.name }}</h3>
              <span class="badge rank">{{ f.rank }}</span>
            </div>
            <div class="meta">{{ f.university }} · {{ f.school }}</div>
            <div class="badges">
              <span v-for="t in f.tags" :key="t" class="badge">{{ t }}</span>
              <span v-if="f.title && f.title !== f.rank" class="badge">{{ f.title }}</span>
            </div>
            <div v-if="f.direction" class="dir">研究方向：{{ f.direction }}</div>
            <div class="links">
              <a v-if="f.orcid" class="orcid" :href="'https://orcid.org/' + f.orcid"
                 target="_blank" rel="noopener noreferrer">ORCID {{ f.orcid }} ↗</a>
              <a v-if="f.source" :href="f.source" target="_blank" rel="noopener noreferrer">来源页面 ↗</a>
            </div>
          </article>
        </div>
        <div v-else class="state">
          <h3>没有匹配的教师</h3>
          <p>试试换个关键词，或点击「重置」清除筛选条件。</p>
          <button class="btn small" type="button" @click="reset">重置筛选</button>
        </div>
      </template>

      <!-- 按学校 -->
      <template v-else>
        <div class="result-line"><strong>{{ filteredSchools.length }}</strong> 所高校</div>
        <div v-if="filteredSchools.length" class="grid">
          <article v-for="s in filteredSchools" :key="s.name" class="card school-card">
            <div class="head">
              <h3>{{ s.name }}</h3>
              <div class="counts">{{ s.city }}<br />{{ s.count }} 位教师 · {{ s.orcid }} 位有 ORCID</div>
            </div>
            <div class="badges">
              <span v-for="t in s.tags" :key="t" class="badge">{{ t }}</span>
            </div>
            <div class="badges">
              <span v-for="d in [...s.discs]" :key="d" class="badge">{{ d }}</span>
            </div>
            <div class="dir">
              <template v-for="(n, r) in s.byRank" :key="r">{{ r }} {{ n }} · </template>
            </div>
            <div class="links">
              <button class="btn small" type="button"
                      @click="openSchool = openSchool === s.name ? null : s.name">
                {{ openSchool === s.name ? '收起名单' : '展开名单（' + s.count + '）' }}
              </button>
            </div>
            <div v-if="openSchool === s.name" class="fac-list">
              <div v-for="p in peopleOf(s.name)" :key="p.id" class="row">
                <span>{{ p.name }}<em v-if="p.direction" class="muted"> — {{ p.direction.slice(0, 40) }}{{ p.direction.length > 40 ? '…' : '' }}</em></span>
                <b>{{ p.rank }}</b>
              </div>
            </div>
          </article>
        </div>
        <div v-else class="state"><h3>没有匹配的学校</h3><p>换个筛选条件试试。</p></div>
      </template>
    </template>
  </main>

  <footer>
    <div class="wrap">
      <h2>数据说明</h2>
      <ul>
        <li><strong>姓名与职称</strong>：来自各校院系官网「师资队伍 / 教师名录」栏目页面，按页面上的职称分栏或教师条目原文摘录；每条都附<strong>来源页面</strong>链接，可自行核对。</li>
        <li><strong>研究方向</strong>：摘录自教师详情页中「研究方向 / 研究领域 / 研究兴趣」的原文，页面没写就留空，不做补写。</li>
        <li><strong>ORCID</strong>：优先取来源页面上的 ORCID；其余用 ORCID 公开检索接口按「姓名拼音 + 机构名」匹配，姓名与机构都要对得上，并<em>回到 ORCID 记录本体复核一次</em>，候选人唯一才回填。ORCID 一栏因此覆盖率不高，但它只是辅助线索，引用前请以本人 ORCID 主页为准。</li>
        <li v-if="meta">采集时间：{{ meta.generated_at }}；教师 {{ meta.faculty_count }} 条，覆盖 {{ meta.university_count }} 所高校，其中 {{ meta.with_title }} 条有职称、{{ meta.with_direction }} 条有研究方向、{{ meta.with_orcid }} 条有 ORCID。</li>
        <li><strong>收录范围</strong>：理工科院系的在职教师与研究人员（数学、物理、化学、材料、机械、能源、计算机、电子信息等）。同一所高校可能收录多个院系，卡片上的院系以来源页面为准。</li>
        <li>未收录 ≠ 该院系没有这位老师：部分高校官网为纯前端渲染、改版或无法访问，本次未纳入。信息可能滞后，请以院系官网最新公告为准。</li>
      </ul>
    </div>
  </footer>
</template>
