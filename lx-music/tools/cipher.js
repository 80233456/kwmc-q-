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

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { encryptKuwoQuery, kwUtf8Bytes, kwBase64 }
}
