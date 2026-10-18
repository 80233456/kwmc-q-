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

/* ---------------- lx-music 自定义源注册 ---------------- */
lx.send(lx.EVENT_NAMES.inited, {
  sources: {
    kw: {
      type: 'music',
      actions: ['musicUrl', 'lyric'],
      qualitys: ['128k', '320k', 'flac', 'flac24bit'],
    },
  },
})

lx.on(lx.EVENT_NAMES.request, async({ source, action, info }) => {
  if (source !== 'kw') throw new Error('不支持的音源: ' + source)
  const meta = (info && info.musicInfo && info.musicInfo.meta) || {}
  const songId = meta.songId != null ? String(meta.songId) : ''
  if (!songId) throw new Error('缺少歌曲 ID')
  switch (action) {
    case 'musicUrl':
      return kwGetMusicUrl(songId, info.type)
    case 'lyric':
      return (await kwGetLyric(songId, info.musicInfo && info.musicInfo.name,
        info.musicInfo && info.musicInfo.singer)) || { lyric: '' }
    default:
      throw new Error('不支持的操作: ' + action)
  }
})
