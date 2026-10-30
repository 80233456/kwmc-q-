/**
 * Test the generated lx-music custom source in a mock sandbox with REAL network.
 * Usage: node test_source.js
 */
const fs = require('fs')
const path = require('path')
const vm = require('vm')
const http = require('http')
const https = require('https')

const code = fs.readFileSync(path.join(__dirname, 'kwlx-kuwo-source.js'), 'utf8')

/* ---- mock lx (mirrors preload.js semantics) ---- */
let initPayload = null
let requestHandler = null

function lxRequest(url, opts, cb) {
  const u = new URL(url)
  const mod = u.protocol === 'https:' ? https : http
  const req = mod.request(url, { method: opts.method || 'GET', headers: opts.headers || {} }, (res) => {
    const chunks = []
    res.on('data', (c) => chunks.push(c))
    res.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8')
      let body = raw
      try { body = JSON.parse(raw) } catch (_) {}
      cb(null, { statusCode: res.statusCode, statusMessage: res.statusMessage, headers: res.headers, body }, body)
    })
  })
  req.on('error', (e) => cb(e, null, null))
  req.setTimeout(opts.timeout || 20000, () => req.destroy(new Error('timeout')))
  req.end()
  return () => req.destroy()
}

const sandbox = {
  lx: {
    EVENT_NAMES: { request: 'request', inited: 'inited', updateAlert: 'updateAlert' },
    request: lxRequest,
    send: (name, data) => { if (name === 'inited') initPayload = data; return Promise.resolve() },
    on: (name, handler) => { if (name === 'request') requestHandler = handler; return Promise.resolve() },
    version: '2.0.0',
    env: 'desktop',
  },
  console,
  setTimeout,
  clearTimeout,
  URL,
}
vm.createContext(sandbox)
vm.runInContext(code, sandbox, { filename: 'kwlx-kuwo-source.js' })

const K = { ok: 0, fail: 0 }
function log(ok, msg) {
  console.log((ok ? '  [OK]   ' : '  [FAIL] ') + msg)
  ok ? K.ok++ : K.fail++
}

async function head(url, n) {
  return new Promise((resolve, reject) => {
    const u = new URL(url)
    const mod = u.protocol === 'https:' ? https : http
    const req = mod.get(url, { headers: { 'User-Agent': 'okhttp/3.10.0', Range: 'bytes=0-' + (n - 1) } }, (res) => {
      const chunks = []
      res.on('data', (c) => chunks.push(c))
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, buf: Buffer.concat(chunks) }))
    })
    req.on('error', reject)
    req.setTimeout(20000, () => req.destroy(new Error('timeout')))
  })
}

async function main() {
  console.log('=== 1) inited payload ===')
  log(!!initPayload, 'inited 已发送')
  if (initPayload) {
    const src = initPayload.sources && initPayload.sources.kw
    log(!!src, 'kw 源已注册: ' + JSON.stringify(src))
    log(!!src && src.qualitys.includes('flac'), '声明了 flac 无损档位')
    log(!!src && src.actions.includes('musicUrl'), '声明了 musicUrl')
  }

  const RID = '28423286' // 富士山下
  const call = (action, type) => requestHandler({
    source: 'kw',
    action,
    info: {
      type,
      musicInfo: { name: '富士山下', singer: '陈奕迅', meta: { songId: RID } },
    },
  })

  console.log('\n=== 2) musicUrl / flac（无损） ===')
  try {
    const url = await call('musicUrl', 'flac')
    log(typeof url === 'string' && /^https?:/.test(url), '返回 URL: ' + String(url).slice(0, 70))
    const r = await head(url, 4096)
    log(['fLaC', 'OggS', 'ID3', 'RIFF'].some((m) => r.buf.slice(0, 4).toString('latin1') === m) ||
      r.buf.slice(0, 3).toString('latin1') === 'ID3' || r.buf[0] === 0xff,
      '文件头: ' + JSON.stringify(r.buf.slice(0, 4).toString('latin1')))
    const cr = r.headers['content-range'] || ''
    const size = Number((/\/(\d+)$/.exec(cr) || [])[1] || 0)
    log(size > 1_000_000, '文件大小: ' + (size / 1048576).toFixed(1) + ' MB')
  } catch (e) { log(false, 'flac 失败: ' + e.message) }

  console.log('\n=== 3) musicUrl / 320k ===')
  try {
    const url = await call('musicUrl', '320k')
    log(typeof url === 'string', '返回 URL: ' + String(url).slice(0, 70))
    const r = await head(url, 2048)
    log(r.buf[0] === 0xff || r.buf.slice(0, 3).toString('latin1') === 'ID3', '看起来是 MP3 帧')
  } catch (e) { log(false, '320k 失败: ' + e.message) }

  console.log('\n=== 4) musicUrl / flac24bit（应回退） ===')
  try {
    const url = await call('musicUrl', 'flac24bit')
    log(typeof url === 'string', '回退成功: ' + String(url).slice(0, 70))
  } catch (e) { log(false, 'flac24bit 失败: ' + e.message) }

  console.log('\n=== 5) lyric ===')
  try {
    const res = await call('lyric')
    const lines = String(res && res.lyric || '').split('\n').filter((x) => x.trim())
    log(lines.length > 5, '歌词 ' + lines.length + ' 行，首行: ' + (lines[0] || '').slice(0, 42))
  } catch (e) { log(false, 'lyric 失败: ' + e.message) }

  console.log('\n=== 6) 异常输入 ===')
  try {
    await requestHandler({ source: 'kw', action: 'musicUrl', info: { type: 'flac', musicInfo: { meta: {} } } })
    log(false, '缺少 songId 未报错')
  } catch (e) { log(true, '缺少 songId 正确报错: ' + e.message) }
  try {
    await requestHandler({ source: 'wy', action: 'musicUrl', info: { musicInfo: { meta: { songId: '1' } } } })
    log(false, '错误 source 未报错')
  } catch (e) { log(true, '错误 source 正确报错: ' + e.message) }

  console.log('\n=== 7) kg 源（跨源解析：按歌名+歌手找酷我 rid）===')
  try {
    const url = await requestHandler({
      source: 'kg',
      action: 'musicUrl',
      info: { type: 'flac', musicInfo: { name: '一直很安静', singer: '阿桑', meta: { songId: 'whatever' } } },
    })
    log(typeof url === 'string' && /^https?:/.test(url), 'kg 歌曲跨源拿到 URL: ' + String(url).slice(0, 70))
    const r = await head(url, 2048)
    log(r.buf.slice(0, 4).toString('latin1') === 'fLaC' || r.buf[0] === 0xff ||
      r.buf.slice(0, 3).toString('latin1') === 'ID3', '文件头正常: ' + JSON.stringify(r.buf.slice(0, 4).toString('latin1')))
  } catch (e) { log(false, 'kg 跨源失败: ' + e.message) }

  console.log(`\nresult: ${K.ok} passed / ${K.fail} failed`)
  process.exit(K.fail === 0 ? 0 : 1)
}

main().catch((e) => { console.error('fatal:', e); process.exit(1) })
