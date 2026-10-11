#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""裁剪 + 放大指定区域，便于细看 UI 细节。用法:
   python work/crop.py <png> <x> <y> <w> <h> <放大倍数> [输出名]"""
import os
import sys

from PIL import Image

src = sys.argv[1]
x, y, w, h = (int(v) for v in sys.argv[2:6])
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
out = sys.argv[7] if len(sys.argv) > 7 else os.path.splitext(src)[0] + "_crop.png"
im = Image.open(src).convert("RGB")
crop = im.crop((x, y, x + w, y + h))
crop = crop.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
crop.save(out)
print("裁剪 → %s  (%d,%d %dx%d ×%.1f)" % (out, x, y, w, h, scale))
