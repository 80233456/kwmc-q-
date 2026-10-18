#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 lx-music 自定义源脚本：头部注释 + 已对拍的 cipher（内联）+ lx 逻辑。"""
import io
import os

ROOT = r"D:\project\kwlx"
HEADER = """/*!
 * @name 酷我音源 · kwlx
 * @description 基于酷我私有接口的音源：q 参数加密 + 无损 FLAC（含 24bit 档位回退）+ 歌词；支持 128k/320k/flac/flac24bit
 * @version 1.0.0
 * @author kwlx
 * @homepage https://github.com/80233456/kwmc-q-
 */
/* ============================================================
 * 说明
 *  - q 参数加密为自定义 DES 变体（密钥 ylzsxkwm），移植自
 *    https://github.com/JayZorn-LJZ/GetFreeMusicYourself ，已与 Python 实现逐字节对拍
 *  - 歌词走酷我 H5 的 **http** 接口（https 会被限流）
 *  - 若 lx-music 版本把 kw 的 actions 限定为 ['musicUrl']，歌词会被忽略；
 *    kwlx 定制版已放开为 ['musicUrl','lyric']，故歌词可用
 * ============================================================ */
"""


def read(p):
    with io.open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def main():
    cipher = read("cipher.js")
    # 去掉 Node 导出块，包成 IIFE 暴露 kwCipher
    idx = cipher.find("if (typeof module !== 'undefined'")
    if idx > 0:
        cipher = cipher[:idx].rstrip()
    part = read("source-lx-part.js")

    body = (
        HEADER
        + "\n'use strict'\n\n"
        + "/* ================= 内联：q 参数加解密（纯 JS，无 Buffer） ================= */\n"
        + "const kwCipher = (function () {\n"
        + "\n".join(("  " + ln) if ln.strip() else ln for ln in cipher.splitlines())
        + "\n  return { encryptKuwoQuery: encryptKuwoQuery }\n})()\n\n"
        + "/* ================= lx-music 音源逻辑 ================= */\n"
        + part
    )
    out = os.path.join(ROOT, "kwlx-kuwo-source.js")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print("已生成:", out)
    print("  体积: %.1f KB  行数: %d" % (len(body.encode("utf-8")) / 1024,
                                         body.count("\n") + 1))
    # 语法自检（用 node 检查，不执行）
    import subprocess
    r = subprocess.run(["node", "--check", out], capture_output=True, text=True)
    print("  node --check:", "OK" if r.returncode == 0 else ("失败: " + r.stderr[:300]))


if __name__ == "__main__":
    main()
