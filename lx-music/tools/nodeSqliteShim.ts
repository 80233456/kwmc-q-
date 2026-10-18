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
    const r = this.stmt.run(...this.normalize(args))
    return { changes: r?.changes ?? 0, lastInsertRowid: r?.lastInsertRowid ?? 0 }
  }

  get(...args: BindArgs) {
    return this.stmt.get(...this.normalize(args))
  }

  all(...args: BindArgs) {
    return this.stmt.all(...this.normalize(args))
  }

  /** better-sqlite3 允许把参数放在数组里 */
  private normalize(args: BindArgs): BindArgs {
    if (args.length === 1 && Array.isArray(args[0])) return args[0]
    return args
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
