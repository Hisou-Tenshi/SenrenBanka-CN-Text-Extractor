#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Solve 200's region2 special bytes via adler32 algebra (fixed modular reduction)."""
import sys, zlib
sys.path.insert(0, r"C:\Users\Tenshi\Documents\GitHub\senren_text")
import xp3_extract as x

M = 65521
path = r"C:\Users\Tenshi\Documents\GitHub\senren_text\scn_raw\200・茉子－語らいver1.00.ks.scn"
raw = bytearray(open(path, "rb").read())
h = 0x50335091
base = (h & x.MASK) + x.OFFSET
n = len(raw)
fk = ((h >> 16) ^ h) & 0xFFFFFFFF
r1f, r2f = x.execute_xcode(fk)
Q1, Q2 = r2f >> 16, r2f & 0xFFFF
vQ1, vQ2 = (r1f >> 8) & 0xFF, (r1f >> 16) & 0xFF

buf = bytearray(raw)
for i in range(base, n):
    buf[i] ^= 0xF6
for pos, val in ((Q1, vQ1), (Q2, vQ2)):
    if base <= pos < n:
        buf[pos] ^= val

a, b = 1, 0
for byt in buf:
    a = (a + byt) % M
    b = (b + a) % M
dA = ((h & 0xFFFF) - a) % M
dB = (((h >> 16) - b) % M + M) % M
if dA > M // 2:
    dA -= M
if dB > M // 2:
    dB -= M
print("dA=%d dB=%d" % (dA, dB))

cands = []
for d1 in range(-255, 256):
    if d1 == 0:
        continue
    d2 = dA - d1
    if d2 == 0 or not (-255 <= d2 <= 255):
        continue
    inv2 = pow(d2 % M, -1, M)
    for P1 in range(0, 65536):
        u1 = n - P1
        r = ((dB - d1 * u1) * inv2) % M
        # n - P2 ≡ r (mod M) with P2 in [0, 65535] -> n-P2 in [n-65535, n]
        base_u = n - r
        for k in range(0, 11):
            u2 = base_u - k * M
            P2 = n - u2
            if P2 < 0 or P2 > 65535 or P2 == P1:
                continue
            cands.append((d1, P1, d2, P2))
print("equation candidates:", len(cands))

def deltas_for(y):
    out = {}
    for xx in range(1, 256):
        out[((y ^ xx) - y) % M] = xx
    return out

verified = 0
seen = set()
for d1, P1, d2, P2 in cands:
    m1 = deltas_for(buf[P1])
    x1 = m1.get(d1 % M)
    if x1 is None:
        continue
    m2 = deltas_for(buf[P2])
    x2 = m2.get(d2 % M)
    if x2 is None:
        continue
    key = (P1, x1, P2, x2)
    if key in seen:
        continue
    seen.add(key)
    t = bytearray(buf)
    t[P1] ^= x1
    t[P2] ^= x2
    if zlib.adler32(bytes(t)) & 0xFFFFFFFF == h:
        print("VERIFIED: P1=%d x1=%02X  P2=%d x2=%02X" % (P1, x1, P2, x2))
        open(path + ".fixed", "wb").write(t)
        verified += 1
        if verified >= 3:
            break
print("verified:", verified)
