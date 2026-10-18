/** 主窗口运行时状态：当前 apiSource、可用的 userApi/apis、musicSdk 概览 */
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
  const ev = async (e) => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })
    return r?.exceptionDetails ? 'EXC: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text) : r?.result?.value
  }

  console.log('=== window 上的 lx ===')
  console.log('  keys:', await ev('JSON.stringify(Object.keys(window.lx || {}))'))
  console.log('  apiInitPromise:', await ev('Array.isArray(window.lx && window.lx.apiInitPromise) ? "array(" + window.lx.apiInitPromise.length + ")" : typeof (window.lx && window.lx.apiInitPromise)'))

  console.log('\n=== 拼出可能的设置访问路径 ===')
  for (const expr of [
    'window.lx.appSetting && window.lx.appSetting["common.apiSource"]',
    'window.lx.setting && window.lx.setting["common.apiSource"]',
    'window.__lx_appSetting && window.__lx_appSetting["common.apiSource"]',
  ]) {
    console.log('  ' + expr.slice(0, 60) + ' => ' + JSON.stringify(await ev(String(expr))))
  }

  console.log('\n=== 从 Vue/Pinia 里取 store（尝试常见挂载点）===')
  console.log('  ', await ev(`(() => {
    const app = document.querySelector('#app')
    const el = app && app.__vue_app__
    if (!el) return 'no __vue_app__'
    const cfg = el.config && el.config.globalProperties
    return JSON.stringify({ gp: cfg ? Object.keys(cfg) : null })
  })()`))

  console.log('\n=== 通过全局事件/存储探测当前音源 ===')
  console.log('  localStorage.search.source:', JSON.stringify(await ev('localStorage.getItem("search.source")')))
  console.log('  localStorage keys:', await ev('JSON.stringify(Object.keys(localStorage).slice(0,20))'))

  console.log('\n=== 页面里能否直接调用 getMusicUrl（复现 Api is not found）===')
  console.log('  ', await ev(`(async () => {
    const el = document.querySelector('#app')
    const vapp = el && el.__vue_app__
    if (!vapp) return 'no vue app'
    // 遍历 pinia store 找 musicSdk / userApi
    const pinia = vapp.config.globalProperties.$pinia
    if (!pinia) return 'no pinia'
    const ids = pinia._s ? Array.from(pinia._s.keys()) : []
    const out = { storeIds: ids }
    const ua = pinia._s.get('userApi')
    if (ua) out.userApi = { status: ua.status, message: ua.message, list: (ua.list||[]).map(x=>x.id), apiKeys: Object.keys(ua.apis||{}) }
    const setting = pinia._s.get('setting')
    if (setting) out.apiSource = setting['common.apiSource'] || (setting.setting && setting.setting['common.apiSource'])
    return JSON.stringify(out)
  })()`))
  ws.close()
})().catch((e) => { console.error('fatal:', e); process.exit(1) })
