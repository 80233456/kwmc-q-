const KW_UA_OK = 'okhttp/3.10.0'
const KW_UA_MOBILE = 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36'
const KW_UA_WEB = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36'
const KW_CRED = 'user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1'

// lx-music 的四个音质档位 → 酷我接口参数
const KW_QUALITY = {
  '128k': { format: 'mp3', br: '128kmp3' },
  '320k': { format: 'mp3', br: '320kmp3' },
  flac: { format: 'flac', br: '2000kflac' },
  flac24bit: { format: 'flac', br: '4000kflac' },
}

/** lx.request 的回调式接口 → Promise */
function kwHttp(url, options) {
  const opts = options || {}
  return new Promise((resolve, reject) => {
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      reject(new Error('请求超时'))
    }, (opts.timeout || 20000) + 2000)
    try {
      lx.request(url, {
        method: 'get',
        timeout: opts.timeout || 20000,
        headers: opts.headers || {},
      }, (err, resp, body) => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        if (err) return reject(new Error('网络错误: ' + (err.message || String(err))))
        if (!resp) return reject(new Error('无响应'))
        if (resp.statusCode && resp.statusCode !== 200) return reject(new Error('HTTP ' + resp.statusCode))
        resolve(body)
      })
    } catch (e) {
      settled = true
      clearTimeout(timer)
      reject(e)
    }
  })
}

/** 歌曲地址：按音质尝试，失败自动降级 */
async function kwGetMusicUrl(songId, quality) {
  const primary = KW_QUALITY[quality] || KW_QUALITY['320k']
  const tries = [primary]
  if (quality === 'flac24bit') tries.push(KW_QUALITY.flac)
  if (primary.format === 'flac') tries.push(KW_QUALITY['320k'], KW_QUALITY['128k'])
  else if (primary.br === '320kmp3') tries.push(KW_QUALITY['128k'])

  let lastErr = null
  for (const t of tries) {
    try {
      const plain = KW_CRED + '&type=convert_url2&sig=0&format=' + t.format +
        '&br=' + t.br + '&rid=' + songId
      const q = kwCipher.encryptKuwoQuery(plain)
      const text = await kwHttp('http://mobi.kuwo.cn/mobi.s?f=kuwo&q=' + q, {
        headers: { 'User-Agent': KW_UA_OK },
      })
      const m = /url=(http\S+)/.exec(String(text))
      if (m && m[1].length <= 2000) return m[1]
      lastErr = new Error('接口未返回可用地址')
    } catch (e) {
      lastErr = e
    }
  }
  throw lastErr || new Error('拿不到播放地址')
}

/** 歌词：酷我 H5（必须 http）→ 网易云兜底（按歌名+歌手） */
async function kwGetLyric(songId, name, singer) {
  // 1) 酷我
  try {
    const body = await kwHttp('http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId=' + songId, {
      headers: { 'User-Agent': KW_UA_MOBILE, Referer: 'https://m.kuwo.cn/' },
    })
    const data = typeof body === 'string' ? JSON.parse(body) : body
    const list = data && data.data && data.data.lrclist
    if (Array.isArray(list) && list.length > 0) {
      const lines = list.map((it) => {
        const t = Number(it.time || 0)
        const mm = ('0' + Math.floor(t / 60)).slice(-2)
        const ss = ('0' + Math.floor(t % 60)).slice(-2)
        const cs = ('0' + Math.round((t - Math.floor(t)) * 100)).slice(-2)
        return '[' + mm + ':' + ss + '.' + cs + ']' + (it.lineLyric || '')
      })
      const lyric = lines.join('\n').trim()
      if (lyric) return { lyric: lyric.slice(0, 50000) }
    }
  } catch (e) { /* 继续走兜底 */ }

  // 2) 网易云兜底
  if (!name) return null
  try {
    const kw = encodeURIComponent((name + ' ' + (singer || '')).trim())
    const body = await kwHttp('https://music.163.com/api/search/get?s=' + kw + '&type=1&limit=5', {
      headers: { 'User-Agent': KW_UA_WEB, Referer: 'https://music.163.com/' },
    })
    const songs = (body && body.result && body.result.songs) || []
    for (const s of songs) {
      if (!s || !s.id) continue
      const b2 = await kwHttp('https://music.163.com/api/song/lyric?id=' + s.id + '&lv=-1&kv=-1&tv=-1', {
        headers: { 'User-Agent': KW_UA_WEB, Referer: 'https://music.163.com/' },
      })
      const lrc = b2 && b2.lrc && b2.lrc.lyric
      if (lrc && /\[\d+:\d+/.test(lrc)) return { lyric: String(lrc).slice(0, 50000) }
    }
  } catch (e) { /* 忽略 */ }
  return null
}

/* ---------------- 网易云（wy）：GDAPI 解析 ---------------- */
// 后端: https://music-api.gdstudio.xyz/api.php （星海音乐源 / GDAPI 同源接口）
// br 映射实测: 128→MP3(4.1MB) 192→MP3(6.2MB) 320→MP3(10.4MB) 740→FLAC(50.7MB) 999→FLAC
const GDAPI = 'https://music-api.gdstudio.xyz/api.php'
const WY_BR = { '128k': ['128', '320'], '320k': ['320', '128'], flac: ['740', '320'], flac24bit: ['999', '740', '320'] }
const wyCache = new Map()

async function wyResolve(songId, quality) {
  const list = WY_BR[quality] || ['320', '128']
  const ck = songId + '|' + list.join(',')
  if (wyCache.has(ck)) return wyCache.get(ck)
  let out = null
  for (const br of list) {
    try {
      const url = GDAPI + '?types=url&source=netease&id=' + encodeURIComponent(songId) + '&br=' + br
      const body = await kwHttp(url, { headers: { 'User-Agent': KW_UA_WEB } })
      const j = typeof body === 'string' ? JSON.parse(body) : body
      if (j && typeof j.url === 'string' && /^https?:\/\//.test(j.url)) { out = j.url; break }
    } catch (e) { /* 换下一个码率 */ }
  }
  if (wyCache.size > 300) wyCache.clear()
  wyCache.set(ck, out)
  return out
}

/* ---------------- 跨源：非 kw 歌曲用「歌名+歌手」在酷我找 rid ---------------- */
const kwRidCache = new Map()

async function kwSearchRid(name, singer) {
  const key = ((name || '') + ' ' + (singer || '')).trim()
  if (!key) return null
  const ck = key.toLowerCase()
  if (kwRidCache.has(ck)) return kwRidCache.get(ck)
  const url = 'http://search.kuwo.cn/r.s?all=' + encodeURIComponent(key) +
    '&pn=0&rn=5&reqId=kwlx&client=kt&uid=0&ver=kwplayer_ar_9.2.2.1&vipver=1' +
    '&show_copyright_off=1&newver=1&ft=music&cluster=0&strategy=2012' +
    '&encoding=utf8&rformat=json&vermerge=1&mobi=1&issubtitle=1'
  let rid = null
  try {
    const body = await kwHttp(url, { headers: { 'User-Agent': KW_UA_WEB } })
    // lx 的 lx.request 在响应是合法 JSON 时会**预先转成对象**，这里统一转回字符串再正则取
    const txt = typeof body === 'string' ? body : JSON.stringify(body)
    // 接口返回的 JSON 里可能有未转义的引号（脏数据），用正则逐条取更稳
    const items = txt.split('{"AARTIST"')
    for (let i = 1; i < items.length; i++) {
      const block = items[i]
      const mName = /"SONGNAME":"([^"]*)"/.exec(block)
      const mRid = /"MUSICRID":"MUSIC_(\d+)"/.exec(block)
      if (!mRid) continue
      const songName = mName ? mName[1] : ''
      // 优先取歌名相同（忽略大小写/括号后缀差异）的那条
      const norm = (s) => String(s).toLowerCase().replace(/[\s\-_·]/g, '').replace(/\(.*?\)|（.*?）/g, '')
      if (!rid || norm(songName) === norm(name)) rid = mRid[1]
      if (norm(songName) === norm(name)) break
    }
  } catch (e) {
    rid = null
  }
  kwRidCache.set(ck, rid)
  if (kwRidCache.size > 500) kwRidCache.delete(kwRidCache.keys().next().value)
  return rid
}

/* ---------------- lx-music 自定义源注册 ---------------- */
// 接管全部 5 个源：kw 用自带 songId 精确解析；其它源用歌名+歌手跨源到酷我
const KW_SOURCES = ['kw', 'kg', 'tx', 'wy', 'mg']
const kwSources = {}
for (const s of KW_SOURCES) {
  kwSources[s] = {
    type: 'music',
    actions: ['musicUrl', 'lyric'],
    qualitys: ['128k', '320k', 'flac', 'flac24bit'],
  }
}

lx.send(lx.EVENT_NAMES.inited, { sources: kwSources })

lx.on(lx.EVENT_NAMES.request, async({ source, action, info }) => {
  const musicInfo = (info && info.musicInfo) || {}
  const meta = musicInfo.meta || {}

  // 网易云：优先走 GDAPI 直出（可拿真无损），失败再回退到酷我跨源
  if (source === 'wy' && action === 'musicUrl' && meta.songId != null) {
    const wyUrl = await wyResolve(String(meta.songId), info.type)
    if (wyUrl) return wyUrl
    console.log('[kwlx] wy 直连解析失败，回退酷我跨源:', musicInfo.name)
  }

  let songId = ''
  if (source === 'kw' && meta.songId != null) {
    songId = String(meta.songId)
  } else {
    songId = (await kwSearchRid(musicInfo.name, musicInfo.singer)) || ''
  }
  if (!songId) throw new Error('酷我未找到该歌曲（' + (musicInfo.name || '?') + '）')
  switch (action) {
    case 'musicUrl':
      return kwGetMusicUrl(songId, info.type)
    case 'lyric':
      return (await kwGetLyric(songId, musicInfo.name, musicInfo.singer)) || { lyric: '' }
    default:
      throw new Error('不支持的操作: ' + action)
  }
})
