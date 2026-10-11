#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酷我 q 参数加密/解密（自定义 DES 变体）。

来源：GitHub 项目 JayZorn-LJZ/GetFreeMusicYourself 的 kuwo_query_encryption.py
（经 https://www.cnblogs.com/jayzorn-ljz/p/20007562 的分析文章指引找到）
关键点：密钥 "ylzsxkwm" 是**自定义** S 盒 + 自定义置换表的 DES 变体，
       所以用标准 DES 库永远解不开 —— 这正是我们此前卡住的原因。

用法：
    q  = encrypt_kuwo_query(plain)          # 加密
    pt = decrypt_kuwo_query(q_b64)          # 解密（base64 字符串 → 明文）
"""
import base64
from functools import reduce
from itertools import accumulate
from operator import or_

MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1
SECRET_KEY_SONG = b"ylzsxkwm"

ARRAYLS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
ARRAYLSMASK = [0, 0x100001, 0x300003]
ARRAYE = [31, 0, 1, 2, 3, 4, -1, -1, 3, 4, 5, 6, 7, 8, -1, -1, 7, 8, 9, 10, 11, 12, -1, -1,
          11, 12, 13, 14, 15, 16, -1, -1, 15, 16, 17, 18, 19, 20, -1, -1, 19, 20, 21, 22, 23,
          24, -1, -1, 23, 24, 25, 26, 27, 28, -1, -1, 27, 28, 29, 30, 31, 30, -1, -1]
ARRAYIP1 = [39, 7, 47, 15, 55, 23, 63, 31, 38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53,
            21, 61, 29, 36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27, 34, 2,
            42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25, 32, 0, 40, 8, 48, 16, 56, 24]
ARRAYIP2 = [57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3, 61, 53, 45, 37, 29,
            21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7, 56, 48, 40, 32, 24, 16, 8, 0, 58, 50, 42,
            34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4, 62, 54, 46, 38, 30, 22, 14, 6]
ARRAYMASK = [1 << n for n in range(64)]
ARRAYMASK[-1] = -ARRAYMASK[-1]
ARRAYP = [15, 6, 19, 20, 28, 11, 27, 16, 0, 14, 22, 25, 4, 17, 30, 9, 1, 7, 23, 13, 31, 26, 2,
          8, 18, 12, 29, 5, 21, 10, 3, 24]
ARRAYPC1 = [56, 48, 40, 32, 24, 16, 8, 0, 57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18,
            10, 2, 59, 51, 43, 35, 62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5,
            60, 52, 44, 36, 28, 20, 12, 4, 27, 19, 11, 3]
ARRAYPC2 = [13, 16, 10, 23, 0, 4, -1, -1, 2, 27, 14, 5, 20, 9, -1, -1, 22, 18, 11, 3, 25, 7,
            -1, -1, 15, 6, 26, 19, 12, 1, -1, -1, 40, 51, 30, 36, 46, 54, -1, -1, 29, 39, 50, 44,
            32, 47, -1, -1, 43, 48, 38, 55, 33, 52, -1, -1, 45, 41, 49, 35, 28, 31, -1, -1]
MATRIXNSBOX = [
    [14, 4, 3, 15, 2, 13, 5, 3, 13, 14, 6, 9, 11, 2, 0, 5, 4, 1, 10, 12, 15, 6, 9, 10, 1, 8,
     12, 7, 8, 11, 7, 0, 0, 15, 10, 5, 14, 4, 9, 10, 7, 8, 12, 3, 13, 1, 3, 6, 15, 12, 6, 11,
     2, 9, 5, 0, 4, 2, 11, 14, 1, 7, 8, 13],
    [15, 0, 9, 5, 6, 10, 12, 9, 8, 7, 2, 12, 3, 13, 5, 2, 1, 14, 7, 8, 11, 4, 0, 3, 14, 11,
     13, 6, 4, 1, 10, 15, 3, 13, 12, 11, 15, 3, 6, 0, 4, 10, 1, 7, 8, 4, 11, 14, 13, 8, 0, 6,
     2, 15, 9, 5, 7, 1, 10, 12, 14, 2, 5, 9],
    [10, 13, 1, 11, 6, 8, 11, 5, 9, 4, 12, 2, 15, 3, 2, 14, 0, 6, 13, 1, 3, 15, 4, 10, 14, 9,
     7, 12, 5, 0, 8, 7, 13, 1, 2, 4, 3, 6, 12, 11, 0, 13, 5, 14, 6, 8, 15, 2, 7, 10, 8, 15, 4,
     9, 11, 5, 9, 0, 14, 3, 10, 7, 1, 12],
    [7, 10, 1, 15, 0, 12, 11, 5, 14, 9, 8, 3, 9, 7, 4, 8, 13, 6, 2, 1, 6, 11, 12, 2, 3, 0, 5,
     14, 10, 13, 15, 4, 13, 3, 4, 9, 6, 10, 1, 12, 11, 0, 2, 5, 0, 13, 14, 2, 8, 15, 7, 4, 15,
     1, 10, 7, 5, 6, 12, 11, 3, 8, 9, 14],
    [2, 4, 8, 15, 7, 10, 13, 6, 4, 1, 3, 12, 11, 7, 14, 0, 12, 2, 5, 9, 10, 13, 0, 3, 1, 11,
     15, 5, 6, 8, 9, 14, 14, 11, 5, 6, 4, 1, 3, 10, 2, 12, 15, 0, 13, 2, 8, 5, 11, 8, 0, 15,
     7, 14, 9, 4, 12, 7, 10, 9, 1, 13, 6, 3],
    [12, 9, 0, 7, 9, 2, 14, 1, 10, 15, 3, 4, 6, 12, 5, 11, 1, 14, 13, 0, 2, 8, 7, 13, 15, 5,
     4, 10, 8, 3, 11, 6, 10, 4, 6, 11, 7, 9, 0, 6, 4, 2, 13, 1, 9, 15, 3, 8, 15, 3, 1, 14, 12,
     5, 11, 0, 2, 12, 14, 7, 5, 10, 8, 13],
    [4, 1, 3, 10, 15, 12, 5, 0, 2, 11, 9, 6, 8, 7, 6, 9, 11, 4, 12, 15, 0, 3, 10, 5, 14, 13,
     7, 8, 13, 14, 1, 2, 13, 6, 14, 9, 4, 1, 2, 14, 11, 13, 5, 0, 1, 10, 8, 3, 0, 11, 3, 5, 9,
     4, 15, 2, 7, 8, 12, 15, 10, 7, 6, 12],
    [13, 7, 10, 0, 6, 9, 5, 15, 8, 4, 3, 10, 11, 14, 12, 5, 2, 11, 9, 6, 15, 12, 0, 3, 4, 1,
     14, 13, 1, 2, 7, 8, 1, 2, 12, 15, 10, 4, 0, 3, 13, 14, 6, 9, 7, 8, 9, 6, 15, 1, 5, 12, 3,
     10, 14, 5, 8, 7, 11, 0, 4, 13, 2, 11],
]


def u64(x):
    return x & MASK64


def u32(x):
    return x & MASK32


def bit_transform(table, n, value):
    return u64(reduce(or_, (ARRAYMASK[i] for i in range(n)
                            if (idx := table[i]) >= 0 and (value & ARRAYMASK[idx]) != 0), 0))


def des64(sub_keys, value):
    out = bit_transform(ARRAYIP2, 64, value)
    left_right = [u32(out), u32((out & 0xFFFFFFFF00000000) >> 32)]

    for i in range(16):
        s_out = 0
        right_expanded = bit_transform(ARRAYE, 64, left_right[1]) ^ sub_keys[i]
        sbox_input = [((right_expanded >> (j * 8)) & 0xFF) for j in range(8)]

        for sbi in reversed(range(8)):
            s_out = (s_out << 4) | (MATRIXNSBOX[sbi][sbox_input[sbi]] & 0xF)

        left_right[0], left_right[1] = (
            left_right[1],
            u32(left_right[0] ^ bit_transform(ARRAYP, 32, s_out)),
        )

    left_right.reverse()
    out = ((left_right[1] << 32) & 0xFFFFFFFF00000000) | (left_right[0] & 0xFFFFFFFF)
    return u64(bit_transform(ARRAYIP1, 64, out))


def build_sub_keys(secret_key=SECRET_KEY_SONG, mode=0):
    key_long = sum((secret_key[i] & 0xFF) << (i * 8) for i in range(8))
    value = bit_transform(ARRAYPC1, 56, u64(key_long))

    def rotate_bits(x, r):
        mask = ARRAYLSMASK[r]
        return u64(u64((x & mask) << (28 - r)) | ((x & u64(~mask)) >> r))

    states = list(accumulate((ARRAYLS[i] for i in range(16)), rotate_bits, initial=value))
    sub_keys = [bit_transform(ARRAYPC2, 64, x) for x in states[1:]]
    return sub_keys[::-1] if mode == 1 else sub_keys


def crypt_blocks(message: bytes, secret_key=SECRET_KEY_SONG, mode=0):
    sub_keys = build_sub_keys(secret_key, mode=mode)
    block_count = len(message) // 8

    blocks = [u64(int.from_bytes(bytes(message[n + m * 8] & 0xFF for n in range(8)), "little"))
              for m in range(block_count)]

    encrypted_blocks = [des64(sub_keys, block) for block in blocks] + [0]

    tail = message[block_count * 8:]
    if len(tail) != 0 or mode == 0:
        tail_long = int.from_bytes(bytes(x & 0xFF for x in tail), "little")
        encrypted_blocks[block_count] = des64(sub_keys, u64(tail_long))

    return bytes((block >> (i * 8)) & 0xFF for block in encrypted_blocks for i in range(8))


def encrypt_kuwo_query(plain_query: str) -> str:
    """明文参数串 → q（base64，标准字母表）。"""
    encrypted = crypt_blocks(plain_query.encode("utf-8"), SECRET_KEY_SONG, mode=0)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_kuwo_query(q_b64: str) -> bytes:
    """q（base64 字符串）→ 明文字节（用反向子密钥解密）。"""
    raw = base64.b64decode(q_b64 + "=" * (-len(q_b64) % 4))
    return crypt_blocks(raw, SECRET_KEY_SONG, mode=1)


if __name__ == "__main__":
    demo = ("user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1"
            "&type=convert_url2&sig=0&format=flac&rid=324244")
    q = encrypt_kuwo_query(demo)
    print("明文 :", demo)
    print("q    :", q)
    print("回解 :", decrypt_kuwo_query(q))
