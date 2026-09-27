<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const view = ref('labs')           // labs | schools | faculty
const query = ref('')
const field = ref('全部')
const tag = ref('全部')
const region = ref('全部')
const school = ref('全部')
const sortBy = ref('学校')
const openSchool = ref(null)

const labs = ref([])
const faculty = ref([])
const meta = ref(null)
const status = ref('loading')      // loading | ready | error
const errorMsg = ref('')

const FIELDS = ['全部', '人工智能', '计算机', '电子信息']
const TAGS = ['全部', '985', '211', '双一流']
const SORTS = ['学校', '课题组', '负责人', '方向']

const REGION_MAP = {
  北京: '北京', 天津: '天津', 上海: '上海',
  南京: '江苏', 苏州: '江苏', 无锡: '江苏', 徐州: '江苏',
  杭州: '浙江', 合肥: '安徽',
  武汉: '湖北', 长沙: '湖南', 广州: '广东', 深圳: '广东', 厦门: '福建', 福州: '福建',
  郑州: '河南', 成都: '四川', 重庆: '重庆',
  西安: '陕西', 兰州: '甘肃', 哈尔滨: '黑龙江', 长春: '吉林', 大连: '辽宁', 沈阳: '辽宁',
  济南: '山东', 青岛: '山东', 昆明: '云南', 乌鲁木齐: '新疆', 南昌: '江西'
}

function normalize(s) {
  return (s || '').toLowerCase()
}

const allSchools = computed(() => {
  const map = new Map()
  for (const l of labs.value) {
    if (!map.has(l.university)) map.set(l.university, { name: l.university, city: l.city, tags: l.tags || [], labs: 0, faculty: 0 })
    map.get(l.university).labs++
  }
  for (const f of faculty.value) {
    if (!map.has(f.university)) map.set(f.university, { name: f.university, city: f.city, tags: f.tags || [], labs: 0, faculty: 0 })
    map.get(f.university).faculty++
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
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
  if (region.value !== '全部' && (REGION_MAP[item.city] || '其他') !== region.value) return false
  if (school.value !== '全部' && item.university !== school.value) return false
  return true
}

const filteredLabs = computed(() => {
  const q = normalize(query.value).trim()
  let list = labs.value.filter((l) => {
    if (!matchesCommon(l)) return false
    if (field.value !== '全部' && l.field !== field.value) return false
    if (!q) return true
    return [l.university, l.school, l.group, l.pi, l.direction, l.city]
      .some((v) => normalize(v).includes(q))
  })
  const key = { 学校: 'university', 课题组: 'group', 负责人: 'pi', 方向: 'direction' }[sortBy.value]
  list = [...list].sort((a, b) => String(a[key]).localeCompare(String(b[key]), 'zh-Hans-CN'))
  return list
})

const filteredSchools = computed(() => {
  const q = normalize(query.value).trim()
  return allSchools.value
    .filter((s) => tag.value === '全部' || (s.tags || []).includes(tag.value))
    .filter((s) => region.value === '全部' || (REGION_MAP[s.city] || '其他') === region.value)
    .filter((s) => field.value === '全部' || labs.value.some((l) => l.university === s.name && l.field === field.value))
    .filter((s) => school.value === '全部' || s.name === school.value)
    .filter((s) => !q || normalize(s.name).includes(q) || normalize(s.city).includes(q))
})

const filteredFaculty = computed(() => {
  const q = normalize(query.value).trim()
  const allow = new Set(filteredSchools.value.map((s) => s.name))
  return faculty.value
    .filter((f) => allow.has(f.university))
    .filter((f) => !q || normalize(f.name).includes(q) || normalize(f.university).includes(q))
})

const schoolsOf = (name) => labs.value.filter((l) => l.university === name)
const facultyOf = (name) => faculty.value.filter((f) => f.university === name)

function reset() {
  query.value = ''
  field.value = '全部'
  tag.value = '全部'
  region.value = '全部'
  school.value = '全部'
  sortBy.value = '学校'
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
    const [l, f, m] = await Promise.all([
      fetch('./labs.json').then((r) => { if (!r.ok) throw new Error('labs.json ' + r.status); return r.json() }),
      fetch('./faculty.json').then((r) => { if (!r.ok) throw new Error('faculty.json ' + r.status); return r.json() }),
      fetch('./meta.json').then((r) => { if (!r.ok) throw new Error('meta.json ' + r.status); return r.json() })
    ])
    labs.value = l
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
        <path d="M12 3 3 7.5l9 4.5 9-4.5z" /><path d="M6 10v5.5c0 1.7 2.7 3 6 3s6-1.3 6-3V10" />
      </svg>
      <span>高校课题组索引</span>
    </div>
    <div class="spacer"></div>
    <span class="nav-stats" v-if="status === 'ready'">
      {{ allSchools.length }} 所高校 · {{ labs.length }} 个课题组 · {{ faculty.length }} 位学者
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
      <div class="eyebrow">985 / 211 · 人工智能 · 计算机 · 电子信息</div>
      <h1>把散落在各校官网的<em>课题组</em>，收进一个可检索的索引</h1>
      <p>
        每条记录都标注了学校、院系、负责人、研究方向与来源页面链接，数据来自各校院系官网与 CSrankings
        公开数据集。信息会随官网变动，报考、套磁或合作前请以院系官网为准。
      </p>
    </section>

    <section class="filters" aria-label="筛选条件">
      <div class="filter-row">
        <label class="sr-only" for="q">搜索</label>
        <input id="q" class="search" v-model="query" type="search"
               placeholder="搜学校、课题组、负责人或研究方向，例如「计算机视觉」" />
        <button class="btn small" type="button" @click="reset">重置</button>
      </div>

      <div class="filter-row">
        <label>学科方向</label>
        <button v-for="f in FIELDS" :key="f" class="chip" type="button"
                :aria-pressed="field === f" @click="field = f">{{ f }}</button>
      </div>

      <div class="filter-row">
        <label>学校层次</label>
        <button v-for="t in TAGS" :key="t" class="chip" type="button"
                :aria-pressed="tag === t" @click="tag = t">{{ t }}</button>
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
      </div>
    </section>

    <div class="tabs" role="tablist" aria-label="视图">
      <button class="tab" role="tab" :aria-selected="view === 'labs'" @click="view = 'labs'">课题组</button>
      <button class="tab" role="tab" :aria-selected="view === 'schools'" @click="view = 'schools'">按学校</button>
      <button class="tab" role="tab" :aria-selected="view === 'faculty'" @click="view = 'faculty'">学者（CSrankings）</button>
    </div>

    <!-- 加载中 -->
    <div v-if="status === 'loading'" class="grid" aria-busy="true">
      <div v-for="n in 6" :key="n" class="skeleton">
        <div class="sk-line w60"></div><div class="sk-line w80"></div><div class="sk-line w40"></div>
      </div>
    </div>

    <!-- 出错 -->
    <div v-else-if="status === 'error'" class="state error" role="alert">
      <h3>数据加载失败</h3>
      <p>{{ errorMsg }}</p>
      <button class="btn small" type="button" @click="load">重试</button>
    </div>

    <template v-else>
      <!-- 课题组 -->
      <template v-if="view === 'labs'">
        <div class="result-line">
          <strong>{{ filteredLabs.length }}</strong> 个课题组
          <span>· 覆盖 {{ new Set(filteredLabs.map((l) => l.university)).size }} 所高校</span>
        </div>
        <div v-if="filteredLabs.length" class="grid">
          <article v-for="(l, i) in filteredLabs" :key="l.university + l.group + i" class="card">
            <h3>{{ l.group }}</h3>
            <div class="meta">{{ l.university }} · {{ l.school }}</div>
            <div class="badges">
              <span class="badge field">{{ l.field }}</span>
              <span v-for="t in l.tags" :key="t" class="badge">{{ t }}</span>
            </div>
            <div class="pi" v-if="l.pi"><b>负责人</b> {{ l.pi }}</div>
            <div class="dir" v-if="l.direction">{{ l.direction }}</div>
            <div class="links">
              <a v-if="l.homepage" :href="l.homepage" target="_blank" rel="noopener noreferrer">课题组主页 ↗</a>
              <a v-if="l.source" :href="l.source" target="_blank" rel="noopener noreferrer">来源页面 ↗</a>
            </div>
          </article>
        </div>
        <div v-else class="state">
          <h3>没有匹配的课题组</h3>
          <p>试试换个关键词，或点击「重置」清除筛选条件。</p>
          <button class="btn small" type="button" @click="reset">重置筛选</button>
        </div>
      </template>

      <!-- 按学校 -->
      <template v-else-if="view === 'schools'">
        <div class="result-line"><strong>{{ filteredSchools.length }}</strong> 所高校</div>
        <div v-if="filteredSchools.length" class="grid">
          <article v-for="s in filteredSchools" :key="s.name" class="card school-card">
            <div class="head">
              <h3>{{ s.name }}</h3>
              <div class="counts">{{ s.city }}<br />{{ s.labs }} 个课题组 · {{ s.faculty }} 位学者</div>
            </div>
            <div class="badges">
              <span v-for="t in s.tags" :key="t" class="badge">{{ t }}</span>
            </div>
            <div v-if="schoolsOf(s.name).length" class="dir">
              {{ schoolsOf(s.name).slice(0, 3).map((l) => l.group).join(' · ') }}{{ schoolsOf(s.name).length > 3 ? ' 等' : '' }}
            </div>
            <div class="links">
              <button class="btn small" type="button"
                      @click="openSchool = openSchool === s.name ? null : s.name">
                {{ openSchool === s.name ? '收起学者名单' : '展开学者名单（' + facultyOf(s.name).length + '）' }}
              </button>
            </div>
            <div v-if="openSchool === s.name" class="fac-list">
              <div v-for="f in facultyOf(s.name)" :key="f.name" class="row">
                <span>{{ f.name }}</span>
                <a v-if="f.homepage" :href="f.homepage" target="_blank" rel="noopener noreferrer">主页 ↗</a>
              </div>
              <p v-if="!facultyOf(s.name).length" class="meta">CSrankings 未收录该校学者。</p>
            </div>
          </article>
        </div>
        <div v-else class="state"><h3>没有匹配的学校</h3><p>换个筛选条件试试。</p></div>
      </template>

      <!-- 学者 -->
      <template v-else>
        <div class="result-line">
          <strong>{{ filteredFaculty.length }}</strong> 位学者
          <span>· 来自 {{ new Set(filteredFaculty.map((f) => f.university)).size }} 所高校 · CSrankings 公开数据集</span>
        </div>
        <div v-if="filteredFaculty.length" class="grid">
          <article v-for="f in filteredFaculty" :key="f.university + f.name" class="card">
            <h3>{{ f.name }}</h3>
            <div class="meta">{{ f.university }} · {{ f.city }}</div>
            <div class="badges"><span v-for="t in f.tags" :key="t" class="badge">{{ t }}</span></div>
            <div class="links">
              <a v-if="f.homepage" :href="f.homepage" target="_blank" rel="noopener noreferrer">个人主页 ↗</a>
            </div>
          </article>
        </div>
        <div v-else class="state"><h3>没有匹配的学者</h3><p>换个筛选条件试试。</p></div>
      </template>
    </template>
  </main>

  <footer>
    <div class="wrap">
      <h2>数据说明</h2>
      <ul>
        <li>课题组条目：来自各校院系官网的研究团队 / 实验室 / 师资栏目页面，每条都给了<strong>来源页面</strong>链接，可自行核对。</li>
        <li>学者条目：来自 CSrankings 公开数据集（按主页域名筛选中国内地高校），仅含该数据集收录的计算机领域教师，不代表院系全量师资。</li>
        <li v-if="meta">采集时间：{{ meta.generated_at }}；课题组 {{ meta.lab_count }} 条，学者 {{ meta.faculty_count }} 条，覆盖 {{ meta.university_count }} 所高校。</li>
        <li>未收录 ≠ 该方向弱：部分高校官网无法访问或团队信息未公开，本次未纳入。信息可能滞后，请以院系官网最新公告为准。</li>
      </ul>
    </div>
  </footer>
</template>
