/*!
 * @name 酷我音源 · kwlx
 * @description 基于酷我私有接口的音源：q 参数加密 + 无损 FLAC（含 24bit 档位回退）+ 歌词；支持 128k/320k/flac/flac24bit
 * @version 1.0.0
 * @author kwlx
 * @homepage https://github.com/80233456/kwmc-q-
 */
/* ============================================================
 * 说明
 *  - q 参数加密为自定义 DES 变体（密钥 ylzsxkwm），移植自
 *    https://github.com/JayZorn-LJZ/GetFreeMusicYourself ，已与 Python 实现逐字节对拍
 *  - 歌词走酷我 H5 的 **http** 接口（https 会被限流）
 *  - 若 lx-music 版本把 kw 的 actions 限定为 ['musicUrl']，歌词会被忽略；
 *    kwlx 定制版已放开为 ['musicUrl','lyric']，故歌词可用
 * ============================================================ */

'use strict'

/* ================= 内联：q 参数加解密（纯 JS，无 Buffer） ================= */
const kwCipher = (function () {
  /**
   * kwlx cipher —— 酷我 q 参数加解密（纯 JS / 无 Buffer、无 require，可直接内联进浏览器沙箱）
   *
   * 算法来源：GitHub 项目 JayZorn-LJZ/GetFreeMusicYourself 的 kuwo_query_encryption.py
   * （经本项目 Python 版 kuwo_q.py 移植，已用 7 组向量与 Python 逐字节对拍一致）
   * 密钥 ylzsxkwm 为自定义 S 盒 + 自定义置换表的 DES 变体；标准 DES 库无法解开。
   */
  const KW_SECRET_KEY = 'ylzsxkwm'

  const KLS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
  const KLSMASK = [0n, 0x100001n, 0x300003n]
  const KE = [31, 0, 1, 2, 3, 4, -1, -1, 3, 4, 5, 6, 7, 8, -1, -1, 7, 8, 9, 10, 11, 12, -1, -1,
    11, 12, 13, 14, 15, 16, -1, -1, 15, 16, 17, 18, 19, 20, -1, -1, 19, 20, 21, 22, 23,
    24, -1, -1, 23, 24, 25, 26, 27, 28, -1, -1, 27, 28, 29, 30, 31, 30, -1, -1]
  const KIP1 = [39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53,
    21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27, 34, 2,
    42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25, 32, 0, 40, 8, 48, 16, 56, 24]
  const KIP2 = [57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3, 61, 53, 45, 37, 29,
    21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7, 56, 48, 40, 32, 24, 16, 8, 0, 58, 50, 42,
    34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38, 30, 22, 14, 6]
  const KMASK = []
  for (let i = 0; i < 64; i++) KMASK.push(1n << BigInt(i))
  const KP = [15, 6, 19, 20, 28, 11, 27, 16, 0, 14, 22, 25, 4, 17, 30, 9, 1, 7, 23, 13, 31, 26, 2,
    8, 18, 12, 29, 5, 21, 10, 3, 24]
  const KPC1 = [56, 48, 40, 32, 24, 16, 8, 0, 57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18,
    10, 2, 59, 51, 43, 35, 62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5,
    60, 52, 44, 36, 28, 20, 12, 4, 27, 19, 11, 3]
  const KPC2 = [13, 16, 10, 23, 0, 4, -1, -1, 2, 27, 14, 5, 20, 9, -1, -1, 22, 18, 11, 3, 25, 7,
    -1, -1, 15, 6, 26, 19, 12, 1, -1, -1, 40, 51, 30, 36, 46, 54, -1, -1, 29, 39, 50, 44,
    32, 47, -1, -1, 43, 48, 38, 55, 33, 52, -1, -1, 45, 41, 49, 35, 28, 31, -1, -1]
  const KSBOX = [
    [14, 4, 3, 15, 2, 13, 5, 3, 13, 14, 6, 9, 11, 2, 0, 5, 4, 1, 10, 12, 15, 6, 9, 10, 1, 8,
      12, 7, 8, 11, 7, 0, 0, 15, 10, 5, 14, 4, 9, 10, 7, 8, 12, 3, 13, 1, 3, 6, 15, 12, 6, 11,
      2, 9, 5, 0, 4, 2, 11, 14, 1, 7, 8, 13],
    [15, 0, 9, 5, 6, 10, 12, 9, 8, 7, 2, 12, 3, 13, 5, 2, 1, 14, 7, 8, 11, 4, 0, 3, 14, 11,
      13, 6, 4, 1, 10, 15, 3, 13, 12, 11, 15, 3, 6, 0, 4, 10, 1, 7, 8, 4, 11, 14, 13, 8, 0, 6,
      2, 15, 9, 5, 7, 1, 10, 12, 14, 2, 5, 9],
    [10, 13, 1, 11, 6, 8, 11, 5, 9, 4, 12, 2, 15, 3, 2, 14, 0, 6, 13, 1, 3, 15, 4, 10, 14, 9,
      7, 12, 5, 0, 8, 7, 13, 1, 2, 4, 3, 6, 12, 11, 0, 13, 5, 14, 6, 8, 15, 2, 7, 10, 8, 15, 4,
      9, 11, 5, 9, 0, 14, 3, 10, 7, 1, 12],
    [7, 10, 1, 15, 0, 12, 11, 5, 14, 9, 8, 3, 9, 7, 4, 8, 13, 6, 2, 1, 6, 11, 12, 2, 3, 0, 5,
      14, 10, 13, 15, 4, 13, 3, 4, 9, 6, 10, 1, 12, 11, 0, 2, 5, 0, 13, 14, 2, 8, 15, 7, 4, 15,
      1, 10, 7, 5, 6, 12, 11, 3, 8, 9, 14],
    [2, 4, 8, 15, 7, 10, 13, 6, 4, 1, 3, 12, 11, 7, 14, 0, 12, 2, 5, 9, 10, 13, 0, 3, 1, 11,
      15, 5, 6, 8, 9, 14, 14, 11, 5, 6, 4, 1, 3, 10, 2, 12, 15, 0, 13, 2, 8, 5, 11, 8, 0, 15,
      7, 14, 9, 4, 12, 7, 10, 9, 1, 13, 6, 3],
    [12, 9, 0, 7, 9, 2, 14, 1, 10, 15, 3, 4, 6, 12, 5, 11, 1, 14, 13, 0, 2, 8, 7, 13, 15, 5,
      4, 10, 8, 3, 11, 6, 10, 4, 6, 11, 7, 9, 0, 6, 4, 2, 13, 1, 9, 15, 3, 8, 15, 3, 1, 14, 12,
      5, 11, 0, 2, 12, 14, 7, 5, 10, 8, 13],
    [4, 1, 3, 10, 15, 12, 5, 0, 2, 11, 9, 6, 8, 7, 6, 9, 11, 4, 12, 15, 0, 3, 10, 5, 14, 13,
      7, 8, 13, 14, 1, 2, 13, 6, 14, 9, 4, 1, 2, 14, 11, 13, 5, 0, 1, 10, 8, 3, 0, 11, 3, 5, 9,
      4, 15, 2, 7, 8, 12, 15, 10, 7, 6, 12],
    [13, 7, 10, 0, 6, 9, 5, 15, 8, 4, 3, 10, 11, 14, 12, 5, 2, 11, 9, 6, 15, 12, 0, 3, 4, 1,
      14, 13, 1, 2, 7, 8, 1, 2, 12, 15, 10, 4, 0, 3, 13, 14, 6, 9, 7, 8, 9, 6, 15, 1, 5, 12, 3,
      10, 14, 5, 8, 7, 11, 0, 4, 13, 2, 11],
  ]

  const M64 = (1n << 64n) - 1n
  const M32 = (1n << 32n) - 1n
  const u64 = (x) => x & M64
  const u32 = (x) => x & M32

  function bitTransform(table, n, value) {
    let out = 0n
    for (let i = 0; i < n; i++) {
      const idx = table[i]
      if (idx < 0) continue
      if ((value & KMASK[idx]) !== 0n) out |= KMASK[i]
    }
    return u64(out)
  }

  function des64(subKeys, value) {
    const out = bitTransform(KIP2, 64, value)
    let l = u32(out)
    let r = u32((out & 0xFFFFFFFF00000000n) >> 32n)
    for (let i = 0; i < 16; i++) {
      const expanded = bitTransform(KE, 64, r) ^ subKeys[i]
      let sOut = 0n
      for (let j = 0; j < 8; j++) {
        const byteVal = Number((expanded >> BigInt(j * 8)) & 0xFFn)
        sOut |= BigInt(KSBOX[j][byteVal] & 0xF) << BigInt(j * 4)
      }
      const nl = r
      const nr = u32(l ^ bitTransform(KP, 32, sOut))
      l = nl
      r = nr
    }
    const outv = ((l << 32n) & 0xFFFFFFFF00000000n) | (r & 0xFFFFFFFFn)
    return u64(bitTransform(KIP1, 64, outv))
  }

  function buildSubKeys(keyStr, mode) {
    let keyLong = 0n
    for (let i = 0; i < 8; i++) keyLong |= BigInt(keyStr.charCodeAt(i) & 0xFF) << BigInt(i * 8)
    let value = bitTransform(KPC1, 56, u64(keyLong))
    const rotate = (x, r) => {
      const mask = KLSMASK[r]
      return u64(u64((x & mask) << BigInt(28 - r)) | ((x & u64(~mask & M64)) >> BigInt(r)))
    }
    let states = [value]
    for (let i = 0; i < 16; i++) {
      value = rotate(value, KLS[i])
      states.push(value)
    }
    let subKeys = states.slice(1).map((x) => bitTransform(KPC2, 64, x))
    if (mode === 1) subKeys = subKeys.slice().reverse()
    return subKeys
  }

  function cryptBlocks(bytes, keyStr, mode) {
    const subKeys = buildSubKeys(keyStr || KW_SECRET_KEY, mode)
    const n = bytes.length
    const blockCount = Math.floor(n / 8)
    const out = []
    for (let m = 0; m < blockCount; m++) {
      let v = 0n
      for (let i = 0; i < 8; i++) v |= BigInt(bytes[m * 8 + i] & 0xFF) << BigInt(i * 8)
      out.push(des64(subKeys, u64(v)))
    }
    out.push(0n)
    if (n - blockCount * 8 !== 0 || mode === 0) {
      let tail = 0n
      for (let i = blockCount * 8; i < n; i++) {
        tail |= BigInt(bytes[i] & 0xFF) << BigInt((i - blockCount * 8) * 8)
      }
      out[blockCount] = des64(subKeys, u64(tail))
    }
    const res = new Uint8Array(out.length * 8)
    for (let i = 0; i < out.length; i++) {
      const b = out[i]
      for (let j = 0; j < 8; j++) res[i * 8 + j] = Number((b >> BigInt(j * 8)) & 0xFFn)
    }
    return res
  }

  /* ---------- 纯 JS 的 UTF-8 / base64（沙箱里没有 Buffer） ---------- */
  function kwUtf8Bytes(str) {
    const out = []
    for (let i = 0; i < str.length; i++) {
      let c = str.charCodeAt(i)
      if (c < 0x80) out.push(c)
      else if (c < 0x800) {
        out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f))
      } else if (c >= 0xd800 && c <= 0xdbff && i + 1 < str.length) {
        const c2 = str.charCodeAt(++i)
        const cp = 0x10000 + ((c - 0xd800) << 10) + (c2 - 0xdc00)
        out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f))
      } else {
        out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f))
      }
    }
    return new Uint8Array(out)
  }

  const KW_B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  function kwBase64(bytes) {
    let out = ''
    for (let i = 0; i < bytes.length; i += 3) {
      const b0 = bytes[i]
      const b1 = i + 1 < bytes.length ? bytes[i + 1] : 0
      const b2 = i + 2 < bytes.length ? bytes[i + 2] : 0
      out += KW_B64[b0 >> 2]
      out += KW_B64[((b0 & 3) << 4) | (b1 >> 4)]
      out += i + 1 < bytes.length ? KW_B64[((b1 & 15) << 2) | (b2 >> 6)] : '='
      out += i + 2 < bytes.length ? KW_B64[b2 & 63] : '='
    }
    return out
  }

  /** 明文查询串 → q（base64） */
  function encryptKuwoQuery(plainQuery, keyStr) {
    return kwBase64(cryptBlocks(kwUtf8Bytes(plainQuery), keyStr, 0))
  }
  return { encryptKuwoQuery: encryptKuwoQuery }
})()

/* ================= lx-music 音源逻辑 ================= */
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
