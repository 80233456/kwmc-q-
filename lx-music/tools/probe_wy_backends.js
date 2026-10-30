/** 对比多个 wy 解析后端：谁能给出真 FLAC */
const http = require('http')
const https = require('https')

function req(url, headers = {}, range) {
  return new Promise((resolve) => {
    let u
    try { u = new URL(url) } catch (e) { return resolve({ err: 'bad url' }) }
    const mod = u.protocol === 'https:' ? https : http
    const h = { 'User-Agent': 'Mozilla/5.0', ...headers }
    if (range) h.Range = range
    const r = mod.get(url, { headers: h, timeout: 15000 }, (res) => {
      const c = []
      res.on('data', (d) => { c.push(d); if (c.length > 40) r.destroy() })
      res.on('end', () => resolve({ status: res.statusCode, buf: Buffer.concat(c), host: u.host }))
      res.on('close', () => resolve({ status: res.statusCode, buf: Buffer.concat(c), host: u.host }))
    })
    r.on('error', (e) => resolve({ err: e.message }))
    r.on('timeout', () => { r.destroy(); resolve({ err: 'timeout' }) })
  })
}

function kind(buf) {
  if (!buf || buf.length < 4) return '空'
  const s = buf.slice(0, 4).toString('latin1')
  if (s === 'fLaC') return 'FLAC ✅'
  if (buf[0] === 0xff || s.slice(0, 3) === 'ID3') return 'MP3'
  if (s.startsWith('<')) return 'HTML(错误页)'
  return JSON.stringify(s)
}

async function tryBackend(name, url, pick) {
  const r = await req(url)
  if (r.err) return console.log(`${name.padEnd(22)} ❌ ${r.err}`)
  let target = null
  try {
    const j = JSON.parse(r.buf.toString('utf8'))
    target = pick(j)
  } catch (e) {
    return console.log(`${name.padEnd(22)} ❌ 非 JSON: ${r.buf.toString('utf8').slice(0, 80)}`)
  }
  if (!target) return console.log(`${name.padEnd(22)} ❌ 无 url（HTTP ${r.status}）`)
  const a = await req(target, { Range: 'bytes=0-2047' }, 'bytes=0-2047')
  if (a.err) return console.log(`${name.padEnd(22)} url=${String(target).slice(0, 50)} ❌ 音频 ${a.err}`)
  console.log(`${name.padEnd(22)} HTTP ${a.status} host=${a.host} 类型=${kind(a.buf)}  url=${String(target).slice(0, 60)}`)
}

;(async () => {
  const ID = 65766 // 富士山下
  console.log('=== 目标: wy id 65766，要求 flac ===')
  await tryBackend('oiapi(flac)', `https://oiapi.net/api/Music_163?id=${ID}&level=flac`, (j) => j.data && j.data[0] && j.data[0].url)
  await tryBackend('oiapi(320k)', `https://oiapi.net/api/Music_163?id=${ID}&level=320k`, (j) => j.data && j.data[0] && j.data[0].url)
  await tryBackend('175.27.166.236', `http://175.27.166.236/wy/wy.php?type=mp3&id=${ID}&level=flac`, (j) => j.url || (j.data && j.data.url) || (j.data && j.data[0] && j.data[0].url))
  await tryBackend('gdstudio(999)', `https://music-api.gdstudio.xyz/api.php?types=url&source=netease&id=${ID}&br=999`, (j) => j.url)
  await tryBackend('gdstudio(320)', `https://music-api.gdstudio.xyz/api.php?types=url&source=netease&id=${ID}&br=320`, (j) => j.url)
  await tryBackend('xcvts', `https://api.xcvts.cn/api/music/wy?msg=${ID}&type=flac`, (j) => j.data && (j.data.url || j.data))
})()
