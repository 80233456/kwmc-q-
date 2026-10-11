#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比多个搜索接口/参数，定位"富士山下 / 不要说话 搜不到"的原因。"""
import json
import re
import sys
import urllib.parse

sys.path.insert(0, ".")
from kuwo_pc_download import http, UA_WEB


def show(tag, txt, limit=6):
    txt = txt.strip()
    try:
        data = json.loads(txt.replace("'", '"'))
    except Exception as e:
        print("   %-28s 解析失败(%s): %s" % (tag, e, txt[:100]))
        return
    lst = data.get("abslist") or data.get("data", {}).get("list") or []
    names = ["%s-%s(%s)" % (i.get("SONGNAME") or i.get("name"),
                            i.get("ARTIST") or i.get("artist"),
                            i.get("MUSICRID") or i.get("rid") or i.get("musicrid"))
             for i in lst[:limit]]
    print("   %-28s 共 %-4s 首: %s" % (tag, data.get("TOTAL") or len(lst), names))
    if not lst:
        print("        原始前 200 字: %s" % txt[:200])


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "富士山下"
    q = urllib.parse.quote(kw)
    print("=== 关键词：%s ===" % kw)

    # A) 我们目前用的（老式 ft=music）
    u = ("http://search.kuwo.cn/r.s?all=%s&pn=0&rn=20&reqId=85bde120-b7b5-11ec-94ee-75d538904202"
         "&client=kt&uid=794762570&ver=kwplayer_ar_9.2.2.1&vipver=1&show_copyright_off=1"
         "&newver=1&ft=music&cluster=0&strategy=2012&encoding=utf8&rformat=json&vermerge=1"
         "&mobi=1&issubtitle=1" % q)
    show("A 当前(ft=music)", http(u, read=200000)[2].decode("utf-8", "replace"))

    # B) App 自己用的参数（searchapi=11 + comprehensive）
    u = ("http://search.kuwo.cn/r.s?client=kt&all=%s&correct=1&stype=comprehensive&cluster=0"
         "&strategy=2012&encoding=utf8&rformat=json&vermerge=1&mobi=1&show_copyright_off=1"
         "&issubtitle=1&isshowshortv=1&searchapi=11&ver=kwplayer_ar_12.2.2.4&vipver=1"
         "&pn=0&rn=20" % q)
    show("B App式(searchapi=11)", http(u, read=300000)[2].decode("utf-8", "replace"))

    # C) 搜索用 itemset / 不同 client
    u = ("http://search.kuwo.cn/r.s?all=%s&ft=music&itemset=web_2013&client=kt&pn=0&rn=20"
         "&rformat=json&encoding=utf8&mobi=1&vipver=1&show_copyright_off=1" % q)
    show("C itemset=web_2013", http(u, read=200000)[2].decode("utf-8", "replace"))

    # D) 移动版 H5 搜索
    u = "https://m.kuwo.cn/newh5app/api/mobile/v1/search/all?key=%s&pn=1&rn=20" % q
    show("D 移动H5 /search/all", http(u, read=200000)[2].decode("utf-8", "replace"))

    # E) 网页版 API
    u = ("https://www.kuwo.cn/api/www/search/searchMusicBykeyWord?key=%s&pn=1&rn=20"
         "&httpsStatus=1&reqId=x" % q)
    show("E 网页API", http(u, {"Referer": "https://www.kuwo.cn/"}, read=200000)[2].decode(
        "utf-8", "replace"))

    # F) 老接口 r.s?stype=comprehensive（无 searchapi）
    u = ("http://search.kuwo.cn/r.s?stype=comprehensive&all=%s&pn=0&rn=20&rformat=json"
         "&encoding=utf8&mobi=1&vipver=1&show_copyright_off=1&strategy=2012&client=kt" % q)
    show("F stype=comprehensive", http(u, read=300000)[2].decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
