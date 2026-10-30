#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 lx-music 仓库规范修「扫描下载目录」按钮：
  规范 1: 所有面向用户的文案必须走 i18n（src/lang/{zh-cn,zh-tw,en-us,ko-kr}.json）
  规范 2: 样式用 less + CSS Modules，禁止内联
  规范 3: 上游 .listsAdd 默认 opacity:.1，悬停才显示；本按钮需要常显 → 增加修饰类
"""
import io
import json
import os

SRC = r"D:\project\kwlx\lx-src"
LANG = os.path.join(SRC, "src/lang")
VUE = os.path.join(SRC, "src/renderer/views/List/MyList/index.vue")

KEYS = {
    "zh-cn": {"lists__scan_download_dir": "扫描下载目录",
              "lists__scan_download_dir_tip": "扫描下载目录，把新增歌曲加入「本地音乐（下载目录）」"},
    "zh-tw": {"lists__scan_download_dir": "掃描下載目錄",
              "lists__scan_download_dir_tip": "掃描下載目錄，把新增歌曲加入「本地音樂（下載目錄）」"},
    "en-us": {"lists__scan_download_dir": "Scan download folder",
              "lists__scan_download_dir_tip": "Scan the download folder and add new songs to the local library"},
    "ko-kr": {"lists__scan_download_dir": "다운로드 폴더 스캔",
              "lists__scan_download_dir_tip": "다운로드 폴더를 스캔해 새 곡을 로컬 라이브러리에 추가합니다"},
}


def patch_lang():
    changed = []
    for loc, kv in KEYS.items():
        p = os.path.join(LANG, "%s.json" % loc)
        if not os.path.exists(p):
            print("  跳过（缺失）:", p)
            continue
        raw = io.open(p, encoding="utf-8").read()
        d = json.loads(raw)
        added = 0
        for k, v in kv.items():
            if k not in d:
                d[k] = v
                added += 1
        if added:
            # 保持 2 空格缩进 + 结尾换行，与上游一致
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, ensure_ascii=False, indent=2) + "\n")
            changed.append("%s(+%d)" % (loc, added))
    return "i18n 键: " + (", ".join(changed) if changed else "已存在")


def patch_vue():
    s = io.open(VUE, encoding="utf-8").read()

    # 1) 按钮：i18n + 常显修饰类
    old_btn = ('        <button :class="$style.listsAdd" aria-label="扫描下载目录" '
               'title="扫描下载目录，把新增歌曲加入「本地音乐（下载目录）」" @click="handleScanLocal">')
    new_btn = ('        <button :class="[$style.listsAdd, $style.listsAlways]" '
               ':aria-label="$t(\'lists__scan_download_dir\')" '
               ':title="$t(\'lists__scan_download_dir_tip\')" @click="handleScanLocal">')
    if old_btn in s:
        s = s.replace(old_btn, new_btn, 1)
    elif "$style.listsAlways" not in s:
        return "⚠ 未找到按钮锚点"

    # 2) 样式：常显修饰类（放在 .listsAdd 块之后）
    if ".listsAlways" not in s:
        anchor = "  &:active {\n    opacity: .7 !important;\n  }"
        if anchor in s:
            s = s.replace(anchor, anchor + "\n  &.listsAlways {\n    opacity: 1;\n  }", 1)
        else:
            return "⚠ 未找到样式锚点"

    io.open(VUE, "w", encoding="utf-8", newline="\n").write(s)
    return "按钮已改为 i18n + 常显"


if __name__ == "__main__":
    print("  ·", patch_lang())
    print("  ·", patch_vue())
    print()
    s = io.open(VUE, encoding="utf-8").read()
    ok = True
    for n, c in [
        ("按钮用 $t 的 aria-label", "$t('lists__scan_download_dir')" in s),
        ("常显修饰类已加", "listsAlways" in s),
        ("样式里有 &.listsAlways", "&.listsAlways" in s),
    ]:
        print("  %s %s" % ("✅" if c else "❌", n))
        ok = ok and c
    for loc in KEYS:
        p = os.path.join(LANG, "%s.json" % loc)
        d = json.load(open(p, encoding="utf-8"))
        has = all(k in d for k in KEYS[loc])
        print("  %s %s 语言键齐全" % ("✅" if has else "❌", loc))
        ok = ok and has
    raise SystemExit(0 if ok else 1)
