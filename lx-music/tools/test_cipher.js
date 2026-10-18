/**
 * Verify the pure-JS cipher (no Buffer) against Python reference vectors.
 * Usage: node test_cipher.js
 */
const fs = require('fs')
const path = require('path')
const { encryptKuwoQuery, kwUtf8Bytes } = require('./cipher.js')

const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, 'vectors.json'), 'utf8'))
let pass = 0
let fail = 0
for (const v of vectors) {
  const q = encryptKuwoQuery(v.plain)
  const same = q === v.q
  if (same) {
    pass++
    console.log(`  [OK]   len=${String(v.plain.length).padStart(3)}  q=${q.slice(0, 28)}...`)
  } else {
    fail++
    console.log(`  [FAIL] len=${v.plain.length}`)
    console.log(`         py=${v.q.slice(0, 90)}`)
    console.log(`         js=${q.slice(0, 90)}`)
  }
  // extra: utf8 round-trip sanity (no Buffer usage)
  const bytes = kwUtf8Bytes(v.plain)
  const back = Buffer.from(bytes).toString('utf8')
  if (back !== v.plain) {
    fail++
    console.log(`  [FAIL] utf8 round-trip: ${JSON.stringify(back).slice(0, 60)}`)
  }
}
console.log(`\nresult: ${pass} passed / ${fail} failed`)
process.exit(fail === 0 ? 0 : 1)
