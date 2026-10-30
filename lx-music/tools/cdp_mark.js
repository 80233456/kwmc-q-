/** 截图并在按钮位置画红框，确认按钮是否真的在那个坐标渲染 */
const fs = require('fs')
const http = require('http')
const WebSocket = require('ws')
const PORT = Number(process.argv[2] || 9243)
const OUT = process.argv[3] || 'D:\\project\\kwlx\\shot_marked.png'

function getJson(p) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => {
      let d = ''
      r.on('data', (c) => (d += c))
      r.on('end', () => { try { res(JSON.parse(d)) } catch (e) { rej(e) } })
    }).on('error', rej)
  })
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

;(async () => {
  const ts = await getJson('/json')
  const pg = ts.find((t) => t.type === 'page' && /index\.html/.test(t.url))
  const ws = new WebSocket(pg.webSocketDebuggerUrl, { perMessageDeflate: false })
  let id = 0
  const send = (m, p = {}) => new Promise((res) => {
    const mid = ++id
    const h = (raw) => { const x = JSON.parse(raw); if (x.id === mid) { ws.off('message', h); res(x.result) } }
    ws.on('message', h)
    ws.send(JSON.stringify({ id: mid, method: m, params: p }))
  })
  await new Promise((r) => ws.on('open', r))
  await send('Runtime.enable')
  await send('DOM.enable')
  const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true }))?.result?.value

  // 先进入「我的列表」页（否则页头不存在）
  await send('Runtime.evaluate', { expression: `(location.hash = '#/list', location.hash)`, returnByValue: true })
  await sleep(2500)

  // 悬停到「我的列表」标题，让上游按钮也显形，便于对比
  const hdr = await ev(`(() => {
    const h = document.querySelector('[class*=listHeader]')
    if (!h) return null
    const r = h.getBoundingClientRect()
    return JSON.stringify({ x: Math.round(r.left + 30), y: Math.round(r.top + r.height / 2) })
  })()`)
  if (hdr) {
    const p = JSON.parse(hdr)
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x, y: p.y })
    await sleep(600)
  }

  const info = await ev(`(() => {
    const b = Array.from(document.querySelectorAll('button')).find(x => /扫描下载目录/.test(x.getAttribute('aria-label')||''))
    if (!b) return null
    const r = b.getBoundingClientRect()
    b.scrollIntoView({ block: 'center' })
    const r2 = b.getBoundingClientRect()
    const cs = getComputedStyle(b)
    const svg = b.querySelector('svg')
    const scs = svg ? getComputedStyle(svg) : null
    return JSON.stringify({
      rect: { x: r2.left, y: r2.top, w: r2.width, h: r2.height },
      btnOpacity: cs.opacity, btnColor: cs.color, btnBg: cs.backgroundColor,
      svgOpacity: scs ? scs.opacity : null, svgFill: scs ? scs.fill : null,
      parentClass: b.parentElement.className, parentOpacity: getComputedStyle(b.parentElement).opacity,
    })
  })()`)
  console.log('按钮实况:', info)

  const shot = await send('Page.captureScreenshot', { format: 'png' })
  if (shot?.data) {
    fs.writeFileSync(OUT, Buffer.from(shot.data, 'base64'))
    console.log('截图:', OUT)
    if (info) {
      const r = JSON.parse(info).rect
      console.log('RECT_FOR_MARK %d %d %d %d' % (Math.round(r.x), Math.round(r.y), Math.round(r.w), Math.round(r.h)))
    }
  }
  ws.close()
})().catch((e) => { console.error(e); process.exit(1) })
