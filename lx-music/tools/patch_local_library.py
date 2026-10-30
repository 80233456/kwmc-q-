#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kwlx 本地音乐库：跟随下载目录自动建库 + 播放音质默认无损
  1) worker 增加 scanLocalMusicDir（递归扫描音频文件）
  2) 新增 useLocalLibrary.ts：启动时/定时把下载目录的歌同步进「本地音乐（下载目录）」列表
  3) 默认播放音质 flac；默认下载目录改到 ~/Music/kwlx；两处都在主进程强制生效
"""
import io
import os
import re

SRC = r"D:\project\kwlx\lx-src"


def rp(p):
    return os.path.join(SRC, p)


def read(p):
    return io.open(rp(p), encoding="utf-8").read()


def write(p, s):
    io.open(rp(p), "w", encoding="utf-8", newline="\n").write(s)


# ---------- 1) worker：目录扫描 ----------
def patch_worker():
    p = "src/renderer/worker/main/list.ts"
    s = read(p)
    if "scanLocalMusicDir" in s:
        return "扫描器已存在，跳过"
    if "import fs from 'node:fs'" not in s:
        s = s.replace("import { SPLIT_CHAR } from '@common/constants'",
                      "import fs from 'node:fs'\nimport path from 'node:path'\n"
                      "import { SPLIT_CHAR } from '@common/constants'", 1)
    add = '''

/**
 * kwlx: 递归扫描一个目录下的音频文件（用于"跟随下载文件夹"自动建库）
 * @param dirPath 目录
 * @param maxDepth 最大深度（默认 6 层）
 */
export const scanLocalMusicDir = async(dirPath: string, maxDepth = 6): Promise<string[]> => {
  const exts = new Set(['.mp3', '.flac', '.ogg', '.oga', '.wav', '.m4a', '.ape', '.aac'])
  const out: string[] = []
  const walk = (dir: string, depth: number) => {
    if (depth > maxDepth) return
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch (_) {
      return
    }
    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        if (e.name.startsWith('.')) continue
        walk(full, depth + 1)
      } else if (e.isFile()) {
        if (exts.has(path.extname(e.name).toLowerCase())) out.push(full)
      }
    }
  }
  if (dirPath && fs.existsSync(dirPath)) walk(dirPath, 0)
  return out
}
'''
    s = s.rstrip() + add
    write(p, s)
    return "已加入 scanLocalMusicDir"


# ---------- 2) 新增 useLocalLibrary.ts ----------
def add_local_library():
    p = "src/renderer/core/useApp/useLocalLibrary.ts"
    if os.path.exists(rp(p)):
        # 覆盖为最新实现
        pass
    code = '''// kwlx: 本地音乐库 —— 跟随"下载目录"自动建库
import { userLists } from '@renderer/store/list'
import { addListMusics, createUserList, getListMusicsFromCache } from '@renderer/store/list/action'
import { appSetting } from '@renderer/store/setting'

const LIST_ID = 'userlist_kwlx_local'
const LIST_NAME = '本地音乐（下载目录）'
const SYNC_INTERVAL = 5 * 60 * 1000

let syncing = false

const ensureList = async(): Promise<string> => {
  const hit = userLists.find(l => l.id == LIST_ID)
  if (hit) return hit.id
  await createUserList({ id: LIST_ID, name: LIST_NAME })
  return LIST_ID
}

/** 把下载目录里的音频同步进本地列表（去重） */
export const syncLocalLibrary = async(force = false) => {
  if (syncing) return
  const dir = appSetting['download.savePath']
  if (!dir) return
  syncing = true
  try {
    const paths = await window.lx.worker.main.scanLocalMusicDir(dir)
    if (!paths.length) return
    const listId = await ensureList()
    let existPaths = new Set<string>()
    try {
      const existed = await getListMusicsFromCache(listId)
      existPaths = new Set((existed ?? []).map((m: any) => m.meta?.filePath).filter(Boolean))
    } catch (_) { /* 首次为空 */ }
    const news = paths.filter(p => !existPaths.has(p))
    if (!news.length) return
    // 每次最多 200 首，避免一次性压垮
    const infos = await window.lx.worker.main.createLocalMusicInfos(news.slice(0, 200))
    if (infos.length) await addListMusics(listId, infos)
    console.log('[kwlx] 本地库同步：', listId, '新增', infos.length, '首（目录共', paths.length, '首）')
  } catch (err) {
    console.warn('[kwlx] 本地库同步失败:', err)
  } finally {
    syncing = false
  }
}

export default () => {
  void syncLocalLibrary(true)
  setInterval(() => { void syncLocalLibrary() }, SYNC_INTERVAL)
}
'''
    write(p, code)
    return "已生成 useLocalLibrary.ts"


# ---------- 3) 启动时调用 ----------
def patch_startup():
    p = "src/renderer/core/useApp/index.ts"
    s = read(p)
    if "useLocalLibrary" in s:
        return "启动钩子已存在，跳过"
    # 找默认导出的函数体，插入调用
    m = re.search(r"(export default \(\) => \{\n)", s)
    if not m:
        return "⚠ useApp/index.ts 结构不符，需人工接入"
    ins = "  useLocalLibrary()\n"
    s = s[:m.end()] + ins + s[m.end():]
    # 加 import
    s = s.replace("import useInitUserApi from './useInitUserApi'",
                  "import useInitUserApi from './useInitUserApi'\nimport useLocalLibrary from './useLocalLibrary'", 1)
    if "useLocalLibrary from './useLocalLibrary'" not in s:
        # 退而求其次：加在第一个 import 之后
        s = s.replace("import ", "import useLocalLibrary from './useLocalLibrary'\nimport ", 1)
    write(p, s)
    return "已在启动流程里调用"


# ---------- 4) 设置默认值 ----------
def patch_settings():
    p = "src/common/defaultSetting.ts"
    s = read(p)
    out = []
    if "'player.playQuality': 'flac'" not in s:
        s = s.replace("'player.playQuality': '128k'", "'player.playQuality': 'flac'")
        out.append("播放音质→flac")
    if "Music', 'kwlx'" not in s:
        s = s.replace("'download.savePath': path.join(os.homedir(), 'Desktop')",
                      "'download.savePath': path.join(os.homedir(), 'Music', 'kwlx')")
        out.append("下载目录→~/Music/kwlx")
    write(p, s)
    return "设置默认值: " + (", ".join(out) if out else "（已是目标值）")


def patch_force_settings():
    p = "src/main/utils/index.ts"
    s = read(p)
    if "'player.playQuality': 'flac'" in s:
        return "主进程强制项已存在，跳过"
    old = """  setting = {
    ...(setting || {}),
    'download.enable': true,
    'list.actionButtonsVisible': true,
  } as LX.AppSetting"""
    new = """  setting = {
    ...(setting || {}),
    'download.enable': true,
    'list.actionButtonsVisible': true,
    // kwlx: 播放音质默认无损（旧存档也一并纠正）
    ...((setting && (setting as any)['player.playQuality'] && (setting as any)['player.playQuality'] != '128k')
      ? {}
      : { 'player.playQuality': 'flac' }),
  } as LX.AppSetting"""
    if old not in s:
        return "⚠ 主进程强制块结构不符，跳过"
    s = s.replace(old, new, 1)
    write(p, s)
    return "主进程已强制 播放音质=flac（仅当仍是 128k 时纠正）"


if __name__ == "__main__":
    for fn in (patch_worker, add_local_library, patch_startup, patch_settings, patch_force_settings):
        print("  ·", fn())
    # 自检
    ok = True
    checks = [
        ("扫描器", "scanLocalMusicDir" in read("src/renderer/worker/main/list.ts")),
        ("本地库模块", os.path.exists(rp("src/renderer/core/useApp/useLocalLibrary.ts"))),
        ("启动接入", "useLocalLibrary" in read("src/renderer/core/useApp/index.ts")),
        ("音质默认无损", "'player.playQuality': 'flac'" in read("src/common/defaultSetting.ts")),
        ("下载目录默认", "Music', 'kwlx'" in read("src/common/defaultSetting.ts")),
        ("主进程强制", "'player.playQuality': 'flac'" in read("src/main/utils/index.ts")),
    ]
    print()
    for n, c in checks:
        print("  %s %s" % ("✅" if c else "❌", n))
        ok = ok and c
    raise SystemExit(0 if ok else 1)
