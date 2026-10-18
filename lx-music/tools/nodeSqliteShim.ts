/* eslint-disable */
// @ts-nocheck
/**
 * node:sqlite 兼容垫片 —— 用 Electron 内置 Node 的 node:sqlite 顶替 better-sqlite3
 *
 * 原因：better-sqlite3 是原生模块，必须按 Electron 的 ABI 编译；本机没有 Visual Studio，
 *      而 Electron 42 内置 Node 24 自带 node:sqlite（DatabaseSync / StatementSync）。
 *
 * 兼容面（项目实际用到的 API）：
 *   new Database(path, { fileMustExist })   文件不存在且 fileMustExist → 抛错（保持原行为）
 *   db.exec(sql) / db.prepare(sql).run|get|all / db.pragma(str) / db.transaction(fn) / db.close()
 */
import fs from 'node:fs'
import { DatabaseSync } from 'node:sqlite'

type BindArgs = any[]

export class Statement {
  private stmt: any
  constructor(stmt: any) {
    this.stmt = stmt
  }

  run(...args: BindArgs) {
    const r = this.call('run', args)
    return { changes: r?.changes ?? 0, lastInsertRowid: r?.lastInsertRowid ?? 0 }
  }

  get(...args: BindArgs) {
    return this.call('get', args)
  }

  all(...args: BindArgs) {
    return this.call('all', args)
  }

  /**
   * better-sqlite3 与 node:sqlite 的关键差异：
   *   - 多余的命名参数：better-sqlite3 **忽略**，node:sqlite **抛错** Unknown named parameter
   *   - 缺失的命名参数：better-sqlite3 绑成 NULL，node:sqlite **抛错** Missing named parameter
   * 这里双向容错：按报错逐个剔除多余参数 / 补齐缺失参数，直到成功。
   */
  private call(method: string, args: BindArgs) {
    let cur = this.normalize(args)
    for (let i = 0; i < 30; i++) {
      try {
        return this.stmt[method](...cur)
      } catch (err: any) {
        const msg = String(err?.message || err)
        let m = /Unknown named parameter '?([^'\s]+)'?/i.exec(msg)
        if (m) {
          const key = m[1]
          const obj = cur[0]
          if (typeof obj !== 'object' || obj === null || !(key in obj)) throw err
          const next: any = {}
          for (const [k, v] of Object.entries(obj)) if (k !== key) next[k] = v
          cur = [next]
          continue
        }
        m = /Missing named parameter '?([^'\s]+)'?/i.exec(msg)
        if (m) {
          const key = m[1]
          const obj = cur[0]
          if (typeof obj !== 'object' || obj === null) throw err
          cur = [{ ...obj, [key]: null }]
          continue
        }
        throw err
      }
    }
    throw new Error('too many named-parameter fixes')
  }

  /** 单数组参数摊平；undefined → null（better-sqlite3 的 NULL 语义） */
  private normalize(args: BindArgs): BindArgs {
    let a = args
    if (a.length === 1 && Array.isArray(a[0])) a = a[0]
    if (a.length === 1 && a[0] && typeof a[0] === 'object' && !Buffer.isBuffer(a[0])) {
      const obj: any = {}
      for (const [k, v] of Object.entries(a[0])) obj[k] = v === undefined ? null : v
      return [obj]
    }
    return a.map((v) => (v === undefined ? null : v))
  }
}

export default class Database {
  private db: DatabaseSync
  /** 供类型引用（原 better-sqlite3 的 Database.Database 命名空间习惯） */
  static Database = Database

  constructor(path: string, opts: { fileMustExist?: boolean, readonly?: boolean } = {}) {
    if (opts.fileMustExist && !fs.existsSync(path)) {
      const err: NodeJS.ErrnoException = new Error('Cannot open database because the file does not exist: ' + path)
      err.code = 'SQLITE_CANTOPEN'
      throw err
    }
    this.db = new DatabaseSync(path, opts.readonly ? { readOnly: true } : {})
  }

  exec(sql: string) {
    return this.db.exec(sql)
  }

  prepare<BindParameters = any, Result = any>(sql: string): Statement {
    return new Statement(this.db.prepare(sql))
  }

  pragma(statement: string) {
    const r = this.db.prepare('PRAGMA ' + statement).all()
    return r
  }

  transaction<T extends(...args: any[]) => any>(fn: T): T {
    const self = this
    return function (this: any, ...args: any[]) {
      self.db.exec('BEGIN')
      try {
        const result = fn.apply(this, args)
        self.db.exec('COMMIT')
        return result
      } catch (err) {
        try { self.db.exec('ROLLBACK') } catch (_) {}
        throw err
      }
    } as T
  }

  close() {
    this.db.close()
  }

  get inTransaction(): boolean {
    return false
  }
}
