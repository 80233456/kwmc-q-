#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在我的列表页头部加「扫描下载目录」按钮"""
import io
import os
import re

SRC = r"D:\project\kwlx\lx-src"
p = os.path.join(SRC, "src/renderer/views/List/MyList/index.vue")


def read():
    return io.open(p, encoding="utf-8").read()


def write(s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


s = read()
if "handleScanLocal" in s:
    print("按钮已存在，跳过")
    raise SystemExit(0)

# 1) 模板：插在第 2 个按钮（刷新）之后
anchor = '''            <use xlink:href="#icon-refresh" />
          </svg>
        </button>
'''
btn = '''        <button :class="$style.listsAdd" aria-label="扫描下载目录" title="扫描下载目录，把新增歌曲加入「本地音乐（下载目录）」" @click="handleScanLocal">
          <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xlink="http://www.w3.org/1999/xlink" height="70%" viewBox="0 0 24 24" space="preserve">
            <use xlink:href="#icon-musicFolder" />
          </svg>
        </button>
'''
if anchor not in s:
    print("⚠ 未找到模板锚点")
    raise SystemExit(1)
s = s.replace(anchor, anchor + btn, 1)

# 2) script：import
m = re.search(r"(import .*from '@renderer/store/list/action'\n)", s)
if m:
    s = s.replace(m.group(1), m.group(1) +
                  "import { syncLocalLibrary } from '@renderer/core/useApp/useLocalLibrary'\n", 1)
else:
    s = re.sub(r"(<script[^>]*>\n)", r"\1import { syncLocalLibrary } from '@renderer/core/useApp/useLocalLibrary'\n", s, count=1)

# 3) setup 里加方法
m = re.search(r"(setup\([^)]*\) \{\n)", s)
if not m:
    print("⚠ setup() 未找到")
    raise SystemExit(1)
s = s.replace(m.group(1), m.group(1) +
              "    const handleScanLocal = async() => {\n"
              "      try {\n"
              "        await syncLocalLibrary(true)\n"
              "        await getUserLists()\n"
              "        window.toast?.('已扫描下载目录', '本地音乐库')\n"
              "      } catch (e) {\n"
              "        console.warn('[kwlx] 手动扫描失败:', e)\n"
              "      }\n"
              "    }\n", 1)

# 4) 暴露到模板（return 块）
m = re.search(r"(    return \{\n)", s)
if m:
    s = s.replace(m.group(1), m.group(1) + "      handleScanLocal,\n", 1)
else:
    print("⚠ return 块未找到")
    raise SystemExit(1)

# 5) 确保 getUserLists 已导入（若没有则补）
if "getUserLists" not in s:
    s = s.replace("import { syncLocalLibrary } from '@renderer/core/useApp/useLocalLibrary'",
                  "import { syncLocalLibrary } from '@renderer/core/useApp/useLocalLibrary'\n"
                  "import { getUserLists } from '@renderer/store/list/action'", 1)

write(s)
print("✅ 已加入「扫描下载目录」按钮")
for l in s.splitlines():
    if "handleScanLocal" in l or "icon-musicFolder" in l or "getUserLists" in l:
        print("   ", l.strip()[:120])
