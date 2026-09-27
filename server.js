// 极简静态服务器：只依赖 Node 内置模块，用于把 dist/ 部署到 80 端口。
// 用法：node server.js [端口]   （默认 80，需 root）
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize, resolve } from 'node:path'

const PORT = Number(process.argv[2] || process.env.PORT || 80)
const HOST = process.env.HOST || '0.0.0.0'
const ROOT = resolve(process.env.ROOT || 'dist')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8'
}

function safeJoin(root, urlPath) {
  const p = resolve(join(root, normalize(decodeURIComponent(urlPath)).replace(/^(\.\.[/\\])+/, '')))
  return p.startsWith(root) ? p : null
}

async function send(res, file, status, cache) {
  const body = await readFile(file)
  res.writeHead(status, {
    'content-type': MIME[extname(file).toLowerCase()] || 'application/octet-stream',
    'content-length': body.length,
    'cache-control': cache
  })
  res.end(body)
}

const server = createServer(async (req, res) => {
  try {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { allow: 'GET, HEAD' }).end('Method Not Allowed')
      return
    }
    const path = new URL(req.url, 'http://localhost').pathname
    let file = safeJoin(ROOT, path === '/' ? '/index.html' : path)
    if (!file) { res.writeHead(403).end('Forbidden'); return }

    let info = await stat(file).catch(() => null)
    if (info && info.isDirectory()) { file = join(file, 'index.html'); info = await stat(file).catch(() => null) }

    if (info && info.isFile()) {
      const immutable = file.includes(`${ROOT}/assets/`)
      await send(res, file, 200, immutable ? 'public, max-age=31536000, immutable' : 'no-cache')
      return
    }
    // SPA 回退
    await send(res, join(ROOT, 'index.html'), 200, 'no-cache')
  } catch (err) {
    res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' }).end('500 ' + err.message)
  }
})

server.listen(PORT, HOST, () => {
  console.log(`serving ${ROOT} on http://${HOST}:${PORT}`)
})
