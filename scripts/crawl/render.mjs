// 用 Playwright 渲染 JS 驱动的师资页，把最终 DOM 落盘供 Python 侧解析。
// 用法: node render.mjs urls.txt rendered/
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { chromium } from 'playwright'

const [listFile, outDir] = process.argv.slice(2)
const urls = fs.readFileSync(listFile, 'utf8').split('\n').map((s) => s.trim()).filter(Boolean)
fs.mkdirSync(outDir, { recursive: true })

const key = (u) => crypto.createHash('sha1').update(u).digest('hex')

const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] })
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
  locale: 'zh-CN',
  viewport: { width: 1440, height: 2000 },
})

let ok = 0
let fail = 0
let cursor = 0
const WORKERS = Number(process.env.WORKERS || 4)

async function worker() {
  while (cursor < urls.length) {
    const url = urls[cursor]
    cursor += 1
    const page = await ctx.newPage()
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
      await page.waitForTimeout(1500)
      for (let i = 0; i < 6; i += 1) {
        await page.mouse.wheel(0, 2000)
        await page.waitForTimeout(300)
      }
      await page.waitForTimeout(800)
      const html = await page.content()
      fs.writeFileSync(path.join(outDir, key(url) + '.html'), html)
      console.log(`OK   ${url} (${html.length})`)
      ok += 1
    } catch (err) {
      console.log(`ERR  ${url} ${err.message.split('\n')[0]}`)
      fail += 1
    } finally {
      await page.close()
    }
  }
}

await Promise.all(Array.from({ length: WORKERS }, worker))
await browser.close()
console.log(`done ok=${ok} fail=${fail}`)
