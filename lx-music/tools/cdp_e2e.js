/** 端到端：CDP 输入搜索 → 双击非 kw 源歌曲 → 验证播放 */
const http = require('http')
const WebSocket = require('ws')
const PORT = Number(process.argv[2] || 9224)
const KEYWORD = process.argv[3] || '一直很安静'

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
  if (!page) { console.log('未找到主窗口'); process.exit(1) }
  const logs = []
  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false })
  let id = 0
  const send = (m, p = {}) => new Promise((resolve) => {
    const mid = ++id
    const h = (raw) => { const x = JSON.parse(raw); if (x.id === mid) { ws.off('message', h); resolve(x.result) } }
    ws.on('message', h); ws.send(JSON.stringify({ id: mid, method: m, params: p }))
  })
  ws.on('message', (raw) => {
    const m = JSON.parse(raw)
    if (m.method === 'Runtime.consoleAPICalled') logs.push((m.params.args || []).map((a) => a.value ?? a.description ?? a.type).join(' '))
    if (m.method === 'Runtime.exceptionThrown') logs.push('[EXC] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text))
  })
  await new Promise((r) => ws.on('open', r))
  await send('Runtime.enable'); await send('Console.enable')
  const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true }))?.result?.value

  // 0) 首次运行会弹「许可协议」，先点同意
  console.log('=== 0) 检查许可协议弹窗 ===')
  const btns = await ev(`(() => {
    const out = []
    for (const b of document.querySelectorAll('button, [class*=btn], [class*=button], a')) {
      if (!b.offsetParent) continue
      const t = (b.innerText || '').trim()
      if (!t || t.length > 16) continue
      const r = b.getBoundingClientRect()
      out.push({ t, x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) })
    }
    return out
  })()`)
  console.log('  按钮:', JSON.stringify(btns))
  const agree = (btns || []).find((b) => /同意|确定|接受|继续|我已阅读/.test(b.t))
  if (agree) {
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send('Input.dispatchMouseEvent', { type, x: agree.x, y: agree.y, button: 'left', clickCount: 1 })
    }
    console.log('  已点击:', agree.t)
    await sleep(3000)
  } else console.log('  （未发现协议按钮，继续）')

  // 1) 聚焦搜索框并输入关键词
  console.log('=== 1) 搜索:', KEYWORD)
  const box = await ev(`(() => {
    const el = document.querySelector('input[type=search], input[placeholder], input')
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), ph: el.placeholder || '' }
  })()`)
  console.log('  搜索框:', JSON.stringify(box))
  if (!box) { console.log('未找到搜索框'); process.exit(1) }
  for (const type of ['mousePressed', 'mouseReleased']) {
    await send('Input.dispatchMouseEvent', { type, x: box.x, y: box.y, button: 'left', clickCount: 1 })
  }
  await send('Input.insertText', { text: KEYWORD })
  await sleep(400)
  for (const type of ['keyDown', 'keyUp']) {
    await send('Input.dispatchKeyEvent', { type, windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, key: 'Enter', code: 'Enter', text: type === 'keyDown' ? '\r' : undefined })
  }
  await sleep(9000)

  // 2) 找非 kw 源的行
  console.log('\n=== 2) 扫描结果行 ===')
  const rows = await ev(`(() => {
    const out = []
    for (const tr of document.querySelectorAll('tr, .list-item')) {
      if (!tr.offsetParent) continue
      const t = (tr.innerText || '').replace(/\\s+/g, ' ').trim()
      if (!/\\d{2}:\\d{2}/.test(t)) continue
      const src = (t.match(/\\b(kw|kg|tx|wy|mg)\\b/) || [])[1] || '?'
      const r = tr.getBoundingClientRect()
      out.push({ src, t: t.slice(0, 46), x: Math.round(r.left + 140), y: Math.round(r.top + r.height / 2) })
      if (out.length >= 10) break
    }
    return out
  })()`)
  for (const r of rows || []) console.log('  ', JSON.stringify(r))
  const target = (rows || []).find((r) => r.src !== 'kw') || (rows || [])[0]
  if (!target) { console.log('无结果行'); process.exit(1) }

  // 3) 双击
  console.log(`\n=== 3) 双击「${target.t}」（源=${target.src}）===`)
  logs.length = 0
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: target.x, y: target.y })
  for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x: target.x, y: target.y, button: 'left', clickCount: 1 })
  await sleep(60)
  for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x: target.x, y: target.y, button: 'left', clickCount: 2 })
  await sleep(15000)

  console.log('\n=== 4) 我们的音源请求 ===')
  const kw = logs.filter((l) => /mobi\.kuwo|kw-er\.kuwo|search\.kuwo|convert_url2/i.test(l))
  if (!kw.length) console.log('  ⚠ 无')
  for (const l of kw.slice(-6)) console.log('  ' + l.slice(0, 130))

  const errs = logs.filter((l) => /EXC|Error/i.test(l))
  if (errs.length) { console.log('\n=== 错误 ==='); for (const l of errs.slice(-4)) console.log('  ' + l.slice(0, 180)) }

  console.log('\n=== 5) 播放状态 ===')
  console.log('  ' + await ev(`(() => {
    const a = document.querySelector('audio')
    return JSON.stringify({
      src: a?.src ? a.src.slice(0, 100) : null,
      paused: a?.paused ?? null, err: a?.error?.code ?? null,
      dur: a && a.duration ? Math.round(a.duration) : null,
      t: a && a.currentTime ? Math.round(a.currentTime) : null,
      title: (document.querySelector('[class*=song-name]')||{}).innerText || null,
    })
  })()`))
  ws.close()
})().catch((e) => { console.error('fatal:', e); process.exit(1) })
