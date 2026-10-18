#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 kwlx 音源与品牌补丁注入 lx-music-desktop 源码树。幂等，可重复执行。"""
import io
import json
import os
import sys

SRC = r"D:\project\kwlx\lx-src"
SRC_JS = r"D:\project\kwlx\kwlx-kuwo-source.js"
MARK = "kwlx_kuwo"


def read(p):
    with io.open(os.path.join(SRC, p), encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with io.open(os.path.join(SRC, p), "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def patch_seed_source():
    """1) 默认预装音源：首次启动即出现在「自定义源」列表里"""
    script = io.open(SRC_JS, encoding="utf-8").read()
    ts = """// 由 kwlx 构建脚本注入：默认预装的酷我音源（首次启动即生效）
const KWLX_SCRIPT = %s

export const userApis: LX.UserApi.UserApiInfoFull[] = [{
  id: '%s',
  name: '酷我音源 · kwlx',
  description: '酷我私有接口音源：q 参数加密 + 无损 FLAC + 歌词（128k/320k/flac/flac24bit）',
  author: 'kwlx',
  homepage: 'https://github.com/80233456/kwmc-q-',
  version: '1.0.0',
  allowShowUpdateAlert: false,
  script: KWLX_SCRIPT,
}]
""" % (json.dumps(script, ensure_ascii=False), MARK)
    write("src/main/modules/userApi/config/index.ts", ts)
    return "已写入默认音源（脚本 %.1f KB）" % (len(script.encode("utf-8")) / 1024)


def patch_actions():
    """2) 放开 kw 源的 lyric 动作（原版仅允许 musicUrl）"""
    p = "src/main/modules/userApi/renderer/preload.js"
    s = read(p)
    if "kw: ['musicUrl', 'lyric']," in s:
        return "已是放开状态，跳过"
    if "kw: ['musicUrl']," not in s:
        return "⚠ 未找到 kw: ['musicUrl'] 片段，跳过"
    s = s.replace("kw: ['musicUrl'],", "kw: ['musicUrl', 'lyric'],", 1)
    write(p, s)
    return "已放开 kw 的 lyric 动作"


def patch_title():
    """3) 窗口标题"""
    p = "src/renderer/index.html"
    s = read(p)
    if "kwlx Music" in s:
        return "标题已是 kwlx Music，跳过"
    s = s.replace("<title>LX Music</title>", "<title>kwlx Music</title>")
    write(p, s)
    return "已改窗口标题为 kwlx Music"


def patch_brand():
    """4) 应用 ID / 产品名"""
    p = "build-config/build-pack.js"
    s = read(p)
    changed = []
    if "'cn.toside.music.desktop'" in s:
        s = s.replace("appId: 'cn.toside.music.desktop'", "appId: 'cn.kwlx.music.desktop'")
        changed.append("appId")
    if "productName: 'lx-music-desktop'," in s:
        s = s.replace("productName: 'lx-music-desktop',", "productName: 'kwlx-music',")
        changed.append("productName")
    if changed:
        write(p, s)
    return "已改品牌: " + (", ".join(changed) if changed else "（已是目标值）")


if __name__ == "__main__":
    if not os.path.isdir(SRC):
        sys.exit("源码树不存在: " + SRC)
    for fn in (patch_seed_source, patch_actions, patch_title, patch_brand):
        print("  ·", fn())
    # 自检：确认补丁就位
    cfg = read("src/main/modules/userApi/config/index.ts")
    pre = read("src/main/modules/userApi/renderer/preload.js")
    html = read("src/renderer/index.html")
    bp = read("build-config/build-pack.js")
    checks = [
        ("默认音源已注入", MARK in cfg and "酷我音源 · kwlx" in cfg),
        ("脚本内容完整", "encryptKuwoQuery" in cfg and "convert_url2" in cfg),
        ("kw 支持 lyric", "kw: ['musicUrl', 'lyric']," in pre),
        ("标题 kwlx", "kwlx Music" in html),
        ("appId 已改", "cn.kwlx.music.desktop" in bp),
        ("productName 已改", "productName: 'kwlx-music'" in bp),
    ]
    print()
    ok = True
    for name, cond in checks:
        print("  %s %s" % ("✅" if cond else "❌", name))
        ok = ok and cond
    sys.exit(0 if ok else 1)
