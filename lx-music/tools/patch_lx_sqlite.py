#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建补丁 2：用 node:sqlite 垫片替掉 better-sqlite3 + 关闭 electron-builder 原生重建。幂等。"""
import io
import os
import sys

SRC = r"D:\project\kwlx\lx-src"


def read(p):
    with io.open(os.path.join(SRC, p), encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with io.open(os.path.join(SRC, p), "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def patch_db_import():
    """db.ts: 改用垫片；去掉 nativeBinding"""
    p = "src/main/worker/dbService/db.ts"
    s = read(p)
    if "nodeSqliteShim" in s:
        return "db.ts 已是垫片，跳过"
    s = s.replace("import Database from 'better-sqlite3'",
                  "import Database from './nodeSqliteShim'")
    s = s.replace(
        "  const nativeBinding = path.join(__dirname, '../node_modules/better-sqlite3/build/Release/better_sqlite3.node')\n",
        "")
    s = s.replace("      nativeBinding,\n", "")
    # 类型：Database.Database → Database（垫片类）
    s = s.replace("let db: Database.Database", "let db: Database")
    s = s.replace("const initTables = (db: Database.Database)", "const initTables = (db: Database)")
    s = s.replace("export const getDB = (): Database.Database => db",
                  "export const getDB = (): Database => db")
    write(p, s)
    return "db.ts 已切到 node:sqlite 垫片"


def patch_verify_types():
    """verifyDB/migrate 的类型来自 better-sqlite3，改成 any 以免依赖其类型定义"""
    changed = []
    for p in ("src/main/worker/dbService/verifyDB.ts",
              "src/main/worker/dbService/migrate.ts"):
        s = read(p)
        if "import type Database from 'better-sqlite3'" in s:
            s = s.replace("import type Database from 'better-sqlite3'",
                          "import type Database from './nodeSqliteShim'")
            write(p, s)
            changed.append(p)
    return "类型引用已改: " + (", ".join(changed) if changed else "（无需改）")


def patch_builder_config():
    """electron-builder：关闭 @electron/rebuild（本机无 VS，且已不再使用原生模块）"""
    p = "build-config/build-pack.js"
    s = read(p)
    if "npmRebuild: false" in s:
        return "已关闭 npmRebuild，跳过"
    # 在第一个 appId 所在配置对象里插入
    idx = s.find("appId: 'cn.kwlx.music.desktop'")
    if idx < 0:
        idx = s.find("appId:")
    if idx < 0:
        return "⚠ 未找到 appId，跳过"
    line_end = s.find("\n", idx)
    s = s[:line_end + 1] + "  npmRebuild: false,\n" + s[line_end + 1:]
    write(p, s)
    return "已插入 npmRebuild: false"


if __name__ == "__main__":
    for fn in (patch_db_import, patch_verify_types, patch_builder_config):
        print("  ·", fn())
    db = read("src/main/worker/dbService/db.ts")
    bp = read("build-config/build-pack.js")
    checks = [
        ("db.ts 使用垫片", "./nodeSqliteShim" in db),
        ("已移除 nativeBinding", "nativeBinding" not in db),
        ("垫片文件存在", os.path.exists(os.path.join(
            SRC, "src/main/worker/dbService/nodeSqliteShim.ts"))),
        ("关闭 npmRebuild", "npmRebuild: false" in bp),
    ]
    print()
    ok = True
    for n, c in checks:
        print("  %s %s" % ("✅" if c else "❌", n))
        ok = ok and c
    sys.exit(0 if ok else 1)
