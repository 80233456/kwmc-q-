/** 检查 lx 的「User api」沙箱窗口：脚本是否加载、inited 是否成功、是否有异常 */
const http = require('http')
const WebSocket = require('ws')
const PORT = Number(process.argv[2] || 9224)

function getJson(p) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => {
      let d = ''; r.on('data', (c) => (d += c)); r.on('end', () => { try { res(JSON.parse(d)) } catch (e) { rej(e) } })
    }).on('error', rej)
  })
}

;(async () => {
  const ts = await getJson('/json')
  console.log('=== targets ===')
  for (const t of ts) console.log(`  [${t.type}] ${t.title}  ${String(t.url).slice(0, 70)}`)
  const sb = ts.find((t) => t.type === 'page' && !/index\.html/.test(t.url))
  if (!sb) { console.log('未找到沙箱窗口'); return }

  const ws = new WebSocket(sb.webSocketDebuggerUrl, { perMessageDeflate: false })
  const logs = []
  let id = 0
  const send = (m, p = {}) => new Promise((resolve) => {
    const mid = ++id
    const h = (raw) => { const x = JSON.parse(raw); if (x.id === mid) { ws.off('message', h); resolve(x.result) } }
    ws.on('message', h); ws.send(JSON.stringify({ id: mid, method: m, params: p }))
  })
  ws.on('message', (raw) => {
    const m = JSON.parse(raw)
    if (m.method === 'Runtime.consoleAPICalled') logs.push('[console] ' + (m.params.args || []).map((a) => a.value ?? a.description ?? a.type).join(' '))
    if (m.method === 'Runtime.exceptionThrown') logs.push('[EXC] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text))
    if (m.method === 'Log.entryAdded') logs.push('[log:' + m.params.entry.level + '] ' + m.params.entry.text)
  })
  await new Promise((r) => ws.on('open', r))
  await send('Runtime.enable')
  await send('Log.enable')
  const ev = async (e) => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })
    return r?.exceptionDetails ? 'EXC: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text) : r?.result?.value
  }

  console.log('\n=== 沙箱环境 ===')
  console.log('  typeof lx        =', await ev('typeof lx'))
  console.log('  lx.version       =', await ev('lx && lx.version'))
  console.log('  script name      =', await ev('lx && lx.currentScriptInfo && lx.currentScriptInfo.name'))
  console.log('  script version   =', await ev('lx && lx.currentScriptInfo && lx.currentScriptInfo.version'))
  console.log('  EVENT_NAMES      =', await ev('JSON.stringify(lx && lx.EVENT_NAMES)'))

  console.log('\n=== 探测 inited 是否已发送（重复发送应报 "Script is inited"）===')
  console.log('  ', await ev(`(async () => {
    try { await lx.send(lx.EVENT_NAMES.inited, { sources: {} }); return 'second inited accepted?!' }
    catch (e) { return 'rejected: ' + e.message }
  })()`))

  console.log('\n=== 沙箱日志/异常 ===')
  if (!logs.length) console.log('  （无）')
  for (const l of logs.slice(-20)) console.log('  ' + l.slice(0, 260))
  ws.close()
})().catch((e) => { console.error('fatal:', e); process.exit(1) })
