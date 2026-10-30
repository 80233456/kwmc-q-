/**
 * lx-music 自定义源高保真测试台
 * 用法: node wy_harness.js <脚本路径> [关键词] [source]
 * 目的: 在不启动 Electron 的情况下，按上游 preload 的语义加载音源脚本并实测 wy 歌曲
 */
const fs = require('fs')
const http = require('http')
const https = require('https')
const crypto = require('crypto')
const zlib = require('zlib')
const vm = require('vm')

const SCRIPT = process.argv[2]
const KEYWORD = process.argv[3] || '富士山下'
const TARGET_SOURCE = process.argv[4] || 'wy'

const EVENT_NAMES = { request: 'request', inited: 'inited', updateAlert: 'updateAlert' }
const allSources = ['kw', 'kg', 'tx', 'wy', 'mg', 'local']
const supportQualitys = {
  kw: ['128k', '320k', 'flac', 'flac24bit'],
  kg: ['128k', '320k', 'flac', 'flac24bit'],
  tx: ['128k', '320k', 'flac', 'flac24bit'],
  wy: ['128k', '320k', 'flac', 'flac24bit'],
  mg: ['128k', '320k', 'flac', 'flac24bit'],
  local: [],
}
const supportActions = {
  kw: ['musicUrl', 'lyric'],
  kg: ['musicUrl'],
  tx: ['musicUrl'],
  wy: ['musicUrl'],
  mg: ['musicUrl'],
  xm: ['musicUrl'],
  local: ['musicUrl', 'lyric', 'pic'],
}

function reqRaw(url, { method = 'GET', headers = {}, body, form, timeout = 20000 } = {}) {
  return new Promise((resolve) => {
    let u
    try { u = new URL(url) } catch (e) { return resolve({ err: e }) }
    const mod = u.protocol === 'https:' ? https : http
    let payload
    const h = {}
    for (const [k, v] of Object.entries(headers || {})) {
      if (v == null) continue
      // 上游 needle 会净化 header；这里对齐：去掉 CR/LF 等非法字符
      const sv = String(v).replace(/[\x00-\x1f\x7f]+/g, ' ').trim()
      if (!sv) continue
      h[k] = sv
    }
    if (form && typeof form === 'object') {
      payload = new URLSearchParams(form).toString()
      h['Content-Type'] = h['Content-Type'] || 'application/x-www-form-urlencoded'
      h['Content-Length'] = Buffer.byteLength(payload)
    } else if (body !== undefined) {
      payload = typeof body === 'string' ? body : JSON.stringify(body)
      h['Content-Type'] = h['Content-Type'] || 'application/json'
      h['Content-Length'] = Buffer.byteLength(payload)
    }
    const r = mod.request(url, { method: method.toUpperCase(), headers: h, timeout }, (res) => {
      const chunks = []
      res.on('data', (c) => chunks.push(c))
      res.on('end', () => {
        const raw = Buffer.concat(chunks)
        resolve({ statusCode: res.statusCode, statusMessage: res.statusMessage, headers: res.headers, bytes: raw.length, raw })
      })
    })
    r.on('error', (err) => resolve({ err }))
    r.on('timeout', () => { r.destroy(); resolve({ err: new Error('timeout') }) })
    if (payload !== undefined) r.write(payload)
    r.end()
  })
}

function buildLx(state) {
  const events = { request: null }
  const lx = {
    EVENT_NAMES,
    version: '2.0.0',
    env: 'desktop',
    currentScriptInfo: state.scriptInfo,
    request(url, opts = {}, callback) {
      let aborted = false
      void (async () => {
        const r = await reqRaw(url, opts)
        if (aborted) return
        if (r.err) return callback.call(lx, r.err, null, null)
        let body = r.raw.toString()
        try { body = JSON.parse(body) } catch (_) { /* 保持字符串，与上游一致 */ }
        const resp = {
          statusCode: r.statusCode,
          statusMessage: r.statusMessage,
          headers: r.headers,
          bytes: r.bytes,
          raw: r.raw,
          body,
        }
        callback.call(lx, null, resp, body)
      })()
      return () => { aborted = true }
    },
    send(name, data) {
      return new Promise((resolve, reject) => {
        if (name === EVENT_NAMES.inited) {
          if (state.inited) return reject(new Error('Script is inited'))
          state.inited = true
          // 上游过滤逻辑，逐字对齐 preload.js handleInit
          const sourceInfo = { sources: {} }
          try {
            for (const source of allSources) {
              const userSource = data && data.sources && data.sources[source]
              if (!userSource || userSource.type !== 'music') continue
              sourceInfo.sources[source] = {
                type: 'music',
                actions: supportActions[source].filter((a) => userSource.actions.includes(a)),
                qualitys: supportQualitys[source].filter((q) => userSource.qualitys.includes(q)),
              }
            }
          } catch (e) {
            state.initError = e.message
            return reject(e)
          }
          state.sources = sourceInfo.sources
          state.initedInfo = data
          resolve()
        } else if (name === EVENT_NAMES.updateAlert) {
          state.updateAlert = data
          resolve()
        } else reject(new Error('Unknown event name: ' + name))
      })
    },
    on(name, handler) {
      if (name === EVENT_NAMES.request) { events.request = handler; return Promise.resolve() }
      return Promise.reject(new Error('The event is not supported: ' + name))
    },
    utils: {
      crypto: {
        aesEncrypt(buffer, mode, key, iv) {
          const c = crypto.createCipheriv(mode, key, iv)
          return Buffer.concat([c.update(buffer), c.final()])
        },
        rsaEncrypt(buffer, key) {
          const buf = Buffer.concat([Buffer.alloc(128 - buffer.length), buffer])
          return crypto.publicEncrypt({ key, padding: crypto.constants.RSA_NO_PADDING }, buf)
        },
        randomBytes: (n) => crypto.randomBytes(n),
        md5: (s) => crypto.createHash('md5').update(s).digest('hex'),
      },
      buffer: {
        from: (...a) => Buffer.from(...a),
        bufToString: (buf, fmt) => Buffer.from(buf, 'binary').toString(fmt),
      },
      zlib: {
        inflate: (b) => new Promise((res, rej) => zlib.inflate(b, (e, d) => e ? rej(new Error(e.message)) : res(d))),
        deflate: (d) => new Promise((res, rej) => zlib.deflate(d, (e, b) => e ? rej(new Error(e.message)) : res(b))),
      },
    },
  }
  lx.__events = events
  return lx
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
// 音源脚本常发不处理的 Promise 拒绝，测试台不应因此崩溃
process.on('unhandledRejection', (e) => console.log('    [unhandled]', String((e && e.message) || e).slice(0, 120)))
let pass = 0, fail = 0
const ok = (c, m) => { console.log('  ' + (c ? '[OK]  ' : '[FAIL]') + ' ' + m); c ? pass++ : fail++ }

async function callRequest(state, lx, payload, timeout = 25000) {
  return await Promise.race([
    Promise.resolve(lx.__events.request.call({}, payload)),
    new Promise((_, rej) => setTimeout(() => rej(new Error('request timeout')), timeout)),
  ])
}

async function head(url, n = 4096) {
  const r = await reqRaw(url, { headers: { Range: 'bytes=0-' + (n - 1), 'User-Agent': 'Mozilla/5.0' } })
  if (r.err) throw r.err
  return r
}

async function searchWy(keyword) {
  // 网易云官方搜索（与音源无关，用来拿一个真实 wy songId）
  const r = await reqRaw('http://music.163.com/api/search/get?s=' + encodeURIComponent(keyword) + '&type=1&limit=1', {
    headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'http://music.163.com/' },
  })
  if (r.err) throw r.err
  const j = JSON.parse(r.raw.toString())
  const s = j && j.result && j.result.songs && j.result.songs[0]
  if (!s) throw new Error('搜索无结果')
  return { id: String(s.id), name: s.name, singer: (s.artists || s.ar || []).map((a) => a.name).join('/') }
}

;(async () => {
  console.log('=== 音源:', SCRIPT, '===')
  const code = fs.readFileSync(SCRIPT, 'utf8')
  const m = code.match(/\/\*![\s\S]*?\*\//)
  const info = { name: '(unknown)', version: '', description: '', author: '', homepage: '' }
  if (m) {
    for (const k of Object.keys(info)) {
      const mm = new RegExp('@' + (k === 'description' ? 'description' : k) + '\\s+([^\\n*]+)').exec(m[0])
      if (mm) info[k] = mm[1].trim()
    }
  }
  console.log('  声明: %s %s | %s', info.name, info.version, info.description)

  const state = { inited: false, sources: null, scriptInfo: info }
  const lx = buildLx(state)
  const sandbox = {
    lx,
    console: (() => {
      const fmt = (a) => a.map((x) => typeof x === 'object' ? (JSON.stringify(x) || '').slice(0, 160) : String(x).slice(0, 160))
      const log = (...a) => console.log('    [s]', ...fmt(a))
      return {
        log, info: log, debug: log, warn: log,
        error: (...a) => console.log('    [s:err]', ...fmt(a)),
        group: log, groupEnd: () => {}, table: log, trace: () => {},
        time: () => {}, timeEnd: () => {}, count: () => {}, assert: () => {},
      }
    })(),
    Buffer, URL, URLSearchParams, setTimeout, clearTimeout, setInterval, clearInterval, atob, btoa, TextDecoder, TextEncoder,
  }
  sandbox.globalThis = sandbox
  sandbox.window = sandbox

  try {
    vm.runInNewContext(code, sandbox, { filename: SCRIPT, timeout: 20000 })
  } catch (e) {
    ok(false, '脚本加载异常: ' + e.message)
    console.log('\nresult: %d passed / %d failed', pass, fail)
    process.exit(1)
  }
  await sleep(1200)
  ok(state.inited, 'inited 已发送' + (state.initError ? '（错误: ' + state.initError + '）' : ''))
  if (!state.sources) { console.log('\nresult: %d passed / %d failed', pass, fail); process.exit(1) }

  const srcKeys = Object.keys(state.sources)
  ok(srcKeys.length > 0, '注册源: ' + JSON.stringify(srcKeys))
  for (const s of srcKeys) {
    console.log('        %s → actions=%s qualitys=%s', s, JSON.stringify(state.sources[s].actions), JSON.stringify(state.sources[s].qualitys))
  }
  const src = state.sources[TARGET_SOURCE]
  ok(!!src, TARGET_SOURCE + ' 源可用')
  if (!src) { console.log('\nresult: %d passed / %d failed', pass, fail); process.exit(1) }
  ok(src.actions.includes('musicUrl'), TARGET_SOURCE + ' 支持 musicUrl')

  let song
  const keywords = String(KEYWORD).split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  try { song = await searchWy(keywords[0]) } catch (e) { ok(false, '取 wy 歌曲失败: ' + e.message) }
  if (song) {
    const list = []
    for (const kw of keywords) {
      try { list.push(await searchWy(kw)) } catch (e) { console.log('  搜索失败:', kw, e.message) }
    }
    console.log('  测试歌曲: %s', list.map((s) => s.name + '(' + s.id + ')').join(', '))
    for (const s of list) {
      for (const q of ['flac', '320k']) {
        if (!src.qualitys.includes(q)) { console.log('  -- 跳过音质 ' + q + '（未声明）'); continue }
        try {
          const url = await callRequest(state, lx, {
            source: TARGET_SOURCE,
            action: 'musicUrl',
            info: { type: q, musicInfo: { name: s.name, singer: s.singer, songmid: s.id, source: TARGET_SOURCE, meta: { songId: s.id, albumName: '', picUrl: '' } } },
          })
          const okUrl = typeof url === 'string' && /^https?:/.test(url) && url.length <= 2048
          ok(okUrl, '[' + s.name + '] ' + q + ' → ' + String(url).slice(0, 80))
          if (okUrl) {
            const r = await head(url)
            const head4 = r.raw.slice(0, 4).toString('latin1')
            const isFlac = head4 === 'fLaC'
            const isMp3 = r.raw[0] === 0xff || r.raw.slice(0, 3).toString('latin1') === 'ID3'
            ok(r.statusCode === 200 || r.statusCode === 206, '[' + s.name + '] ' + q + ' HTTP ' + r.statusCode + ' 字节=' + r.bytes + ' host=' + (new URL(url).host))
            ok(isFlac || isMp3, '[' + s.name + '] ' + q + ' 文件头 ' + JSON.stringify(head4) + ' → ' + (isFlac ? 'FLAC 无损 ✅' : isMp3 ? 'MP3' : '未知'))
          }
        } catch (e) { ok(false, '[' + s.name + '] ' + q + ' 失败: ' + e.message) }
      }
    }
    console.log('\n  ---- lyric ----')
    if (src.actions.includes('lyric')) {
      try {
        const r = await callRequest(state, lx, { source: TARGET_SOURCE, action: 'lyric', info: { musicInfo: { name: list[0].name, singer: list[0].singer, meta: { songId: list[0].id } } } })
        const lines = r && typeof r.lyric === 'string' ? r.lyric.split('\n').length : 0
        ok(lines > 3, 'lyric 返回 ' + lines + ' 行')
      } catch (e) { ok(false, 'lyric 失败: ' + e.message) }
    } else console.log('  -- 该源未开放 lyric 动作（上游 wy 只允许 musicUrl）')
  }

  console.log('\nresult: %d passed / %d failed', pass, fail)
  process.exit(fail === 0 ? 0 : 1)
})()
