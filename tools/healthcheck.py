#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自检工具：逐条验证程序依赖的关键链路，定位"哪一环失效了"。

用法:
    python tools/healthcheck.py          # 全项自检
    python tools/healthcheck.py --quick  # 跳过整段下载

退出码: 0=全部正常  1=有环节失效（界面仍可用，但对应功能会受影响）
"""
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import kuwo_pc_download as K          # noqa: E402

KW = "富士山下 陈奕迅"
RID = "28423286"
results = []


def check(name, fn, hint=""):
    t0 = time.time()
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, "异常: %s" % str(e)[:80]
    dt = time.time() - t0
    results.append((name, ok, detail, dt, hint))
    print("  %-22s %s  %-46s %5.1fs" % (name, "✅" if ok else "❌", detail[:46], dt))
    return ok


def c_dns():
    """各域名连通性"""
    hosts = ["search.kuwo.cn", "mobi.kuwo.cn", "m.kuwo.cn", "img1.kuwo.cn",
             "music.163.com"]
    bad = []
    for h in hosts:
        try:
            urllib.request.urlopen("http://%s" % h if h.startswith("m.") else
                                   "https://%s" % h, timeout=8)
        except Exception as e:
            code = getattr(e, "code", None)
            if code is None:
                bad.append(h)
    return (not bad), ("全部可达" if not bad else "不可达: " + ",".join(bad))


def c_cipher():
    """q 参数加解密自检（纯本地，不依赖网络）
    注意：解密结果按分组填充 \\x00，比对前要去掉填充。"""
    from kuwo_q import encrypt_kuwo_query, decrypt_kuwo_query
    plain = "user=0&corp=kuwo&type=convert_url2&rid=%s&format=mp3" % RID
    enc = encrypt_kuwo_query(plain)
    dec = decrypt_kuwo_query(enc)
    if isinstance(dec, bytes):
        dec = dec.decode("utf-8", "ignore")
    dec = dec.rstrip("\x00")
    return (dec == plain), ("往返一致（密文 %d 字符）" % len(enc) if dec == plain
                           else "往返不一致: %r" % dec[:60])


def c_search():
    r = K.search(KW)
    if not r:
        return False, "无结果（接口可能变更或被限流）"
    return True, "%d 条，首条: %s" % (len(r), r[0]["name"][:14])


def c_resolve():
    u, f, _b = K.resolve_url(RID, "flac", "2000kflac")
    if not u:
        return False, "拿不到播放地址"
    sz = K.remote_size(u)
    if sz < 1_000_000:
        return False, "地址可用但体积异常(%d B)" % sz
    return True, "%s %.1f MB" % (f, sz / 1048576)


def c_download_head():
    """真下载前 256KB（验证 CDN 真的给数据，而不只是 HEAD 通）"""
    u, _f, _b = K.resolve_url(RID, "mp3", "128kmp3")
    if not u:
        return False, "无地址"
    req = urllib.request.Request(u, headers={"User-Agent": K.UA_OK, "Range": "bytes=0-262143"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return (len(data) >= 65536), ("读到 %d KB" % (len(data) // 1024))


def c_lyric():
    lrc = K.fetch_lyric(RID, "富士山下", "陈奕迅", 259)
    if not lrc:
        return False, "四级降级全部失败"
    n = len([x for x in lrc.splitlines() if x.strip()])
    src = "缓存" if os.path.exists(os.path.join(K.LYRIC_CACHE, RID + ".lrc")) else "在线"
    return True, "%d 行（%s）" % (n, src)


def c_cover():
    r = K.search(KW)
    if not r or not r[0].get("pic_short"):
        return False, "搜索结果无封面字段"
    short = r[0]["pic_short"].split("/")
    url = "https://img1.kuwo.cn/star/albumcover/500/" + "/".join(short[1:])
    req = urllib.request.Request(url, headers={"User-Agent": K.UA_WEB})
    with urllib.request.urlopen(req, timeout=15) as resp:
        d = resp.read()
    return (len(d) > 2000), "%d KB" % (len(d) // 1024)


def main():
    quick = "--quick" in sys.argv
    print("=" * 78)
    print("音乐盒 Studio · 链路自检      （任何一项 ❌ 都只影响对应功能，界面仍可用）")
    print("=" * 78)
    check("网络/域名", c_dns, "检查域名是否被墙/改解析")
    check("q 加密算法", c_cipher, "纯本地，若失败说明 kuwo_q.py 被改动")
    check("搜索接口", c_search, "改 kuwo_pc_download.search() 的 URL/解析")
    check("播放地址解析", c_resolve, "改 resolve_url() 的参数模板")
    if not quick:
        check("真实下载(前256KB)", c_download_head, "CDN 侧变化时看这里")
    check("歌词(四级降级)", c_lyric, "改 fetch_lyric() 或补新音源")
    check("封面", c_cover, "改 cover_url() 的拼接规则")

    bad = [n for n, ok, _d, _t, _h in results if not ok]
    print("-" * 78)
    if not bad:
        print("结论：全部正常 ✅  当前接口与算法均可用。")
    else:
        print("结论：%d 项失效 ❌" % len(bad))
        for n, ok, d, _t, hint in results:
            if not ok:
                print("   · %-20s %s" % (n, d))
                if hint:
                    print("     修复方向：%s" % hint)
        print("  提示：接口随时可能变。先跑 tools/search_probe.py / lyric_probe.py 抓原始响应，")
        print("        再对照 docs/接口速查与维护.md 定位要改的位置。")
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
