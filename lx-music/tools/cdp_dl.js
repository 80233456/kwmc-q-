/** 检查每行是否出现下载按钮（#icon-download）以及行数 */
const http = require('http')
const WebSocket = require('ws')
const PORT = Number(process.argv[2] || 9227)
const KEY = process.argv[3] || '一直很安静'

function getJson(p) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => {
      let d = ''; r.on('data', (c) => (d += c)); r.on('end', () => { try { res(JSON.parse(d)) } catch (e) { rej(e) } })
    }).on('error', rej)
  })
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

;(async () => {
  const ts = await getJson('/json')
  const page = ts.find((t) => t.type === 'page' && /index\.html/.test(t.url))
  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false })
  let id = 0
  const send = (m, p = {}) => new Promise((resolve) => {
    const mid = ++id
    const h = (raw) => { const x = JSON.parse(raw); if (x.id === mid) { ws.off('message', h); resolve(x.result) } }
    ws.on('message', h); ws.send(JSON.stringify({ id: mid, method: m, params: p }))
  })
  await new Promise((r) => ws.on('open', r))
  await send('Runtime.enable')
  const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true }))?.result?.value

  // 先点掉许可协议/任何 OK 按钮
  const okBtn = await ev(`(() => {
    for (const b of document.querySelectorAll('button')) {
      if (!b.offsetParent) continue
      const t = (b.innerText || '').trim()
      if (/好的|OK|同意|确定|接受/.test(t)) {
        const r = b.getBoundingClientRect()
        return JSON.stringify({ t, x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) })
      }
    }
    return null
  })()`)
  if (okBtn) {
    const b = JSON.parse(okBtn)
    for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x: b.x, y: b.y, button: 'left', clickCount: 1 })
    console.log('已点掉协议:', b.t)
    await sleep(2500)
  }

  // 搜索
  const box = await ev(`(() => {
    for (const el of document.querySelectorAll('input')) {
      const r = el.getBoundingClientRect()
      if (r.width > 200 && r.height > 15) return { x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2) }
    }
    return null
  })()`)
  if (!box) { console.log('无可见搜索框'); process.exit(1) }
  for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 })
  await sleep(200)
  await send('Input.insertText', { text: KEY })
  await sleep(300)
  for (const type of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type, windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: 'Enter', code: 'Enter', text: type === 'keyDown' ? '\r' : undefined })
  console.log('已搜索:', KEY)
  await sleep(9000)

  for (const round of [1, 2, 3]) {
    const info = await ev(`(() => {
      const rows = Array.from(document.querySelectorAll('tr, .list-item')).filter(e => e.offsetParent && /\\d{2}:\\d{2}/.test((e.innerText||'')))
      const dl = Array.from(document.querySelectorAll('use[href="#icon-download"], use[*|href="#icon-download"], [aria-label*="下载"]'))
        .filter(e => e.closest('tr, .list-item'))
      const dlVisible = dl.filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 })
      return JSON.stringify({
        rows: rows.length,
        downloadIcons: dl.length,
        downloadVisible: dlVisible.length,
        sampleRow: rows[0] ? (rows[0].innerText||'').replace(/\\s+/g,' ').slice(0,60) : null,
        rowHtmlButtons: rows[0] ? rows[0].querySelectorAll('button').length : 0,
        rowAriaLabels: rows[0] ? Array.from(rows[0].querySelectorAll('button')).map(b=>b.getAttribute('aria-label')) : [],
      })
    })()`)
    console.log(`第 ${round} 次检查:`, info)
    if (info && JSON.parse(info).downloadIcons > 0) break
    await sleep(4000)
  }
  ws.close()
})().catch((e) => { console.error('fatal:', e); process.exit(1) })
