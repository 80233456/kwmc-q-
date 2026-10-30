/** 读取运行时设置：播放音质 / 下载目录 / 下载开关 / 行内按钮 */
const http = require('http')
const WebSocket = require('ws')
const PORT = Number(process.argv[2] || 9235)

function getJson(p) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => {
      let d = ''
      r.on('data', (c) => (d += c))
      r.on('end', () => { try { res(JSON.parse(d)) } catch (e) { rej(e) } })
    }).on('error', rej)
  })
}

;(async () => {
  const ts = await getJson('/json')
  const pg = ts.find((t) => t.type === 'page' && /index\.html/.test(t.url))
  if (!pg) { console.log('无主窗口'); return }
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
  const expr = `(() => {
    const s = (window.lxData && window.lxData.appSetting) || {}
    return JSON.stringify({
      playQuality: s['player.playQuality'],
      savePath: s['download.savePath'],
      downloadEnable: s['download.enable'],
      actionButtons: s['list.actionButtonsVisible'],
      apiSource: s['common.apiSource'],
    })
  })()`
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
  console.log(r?.result?.value ?? '(读取失败)')
  const diag = await send('Runtime.evaluate', { expression: 'JSON.stringify(window.__kwlxDiag || null)', returnByValue: true })
  console.log('diag:', diag?.result?.value)
  ws.close()
})().catch((e) => { console.error(e); process.exit(1) })
