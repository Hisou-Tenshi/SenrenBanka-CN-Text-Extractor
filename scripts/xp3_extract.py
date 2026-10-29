#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XP3 extractor for Yuzusoft Senren Banka (Steam CN) — SenrenCxCrypt scheme.
Ported from GARbro (KiriKiriCx.cs / YuzCrypt.cs / ArcXP3.cs) via yuzu-xp3.
Scheme constants from msg-tool database (lifegpc).
Usage: python xp3_extract.py <archive.xp3> <outdir> [suffix_filter]
"""
import base64
import hashlib
import os
import struct
import sys
import zlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAGIC = b"XP3\x0d\x0a\x20\x0a\x1a\x8b\x67\x01"
M32 = 0xFFFFFFFF

# ---- Senren Banka scheme constants (msg-tool crypt.json) ----
MASK = 308
OFFSET = 1846
PROLOG = list(base64.b64decode("AQAC"))
ODD = list(base64.b64decode("AwECBAAF"))
EVEN = list(base64.b64decode("BwQDBgIAAQU="))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "senren_banka.bin"), "rb") as _f:
    CTRL = list(struct.unpack("<1024I", _f.read(0x1000)))

# ---- xcode VM (CxProgram) ----
BC_NOP, BC_RETN, BC_MOV_EDI_ARG, BC_PUSH_EBX, BC_POP_EBX, BC_PUSH_ECX, BC_POP_ECX = range(7)
BC_MOV_EAX_EBX, BC_MOV_EBX_EAX, BC_MOV_ECX_EBX = 7, 8, 9
BC_MOV_EAX_EDI, BC_MOV_EAX_INDIRECT, BC_ADD_EAX_EBX, BC_SUB_EAX_EBX, BC_IMUL_EAX_EBX = 11, 12, 13, 14, 15
BC_AND_ECX_0F, BC_SHR_EBX_1, BC_SHL_EAX_1, BC_SHR_EAX_CL, BC_SHL_EAX_CL, BC_OR_EAX_EBX = 16, 17, 18, 19, 20, 21
BC_NOT_EAX, BC_NEG_EAX, BC_DEC_EAX, BC_INC_EAX = 22, 23, 24, 25
BC_IMMED = 0x100
BC_MOV_EAX_IMMED, BC_AND_EBX_IMMED, BC_AND_EAX_IMMED = 0x101, 0x102, 0x103
BC_XOR_EAX_IMMED, BC_ADD_EAX_IMMED, BC_SUB_EAX_IMMED = 0x104, 0x105, 0x106
LENGTH_LIMIT = 0x80


class CxProgram:
    def __init__(self, seed):
        self.code = []
        self.rng = seed
        self.length = 0

    def get_random(self):
        seed = self.rng
        self.rng = (1103515245 * seed + 12345) & M32
        return self.rng ^ ((seed << 16) & M32) ^ (seed >> 16)

    def emit_nop(self, count):
        if self.length + count > LENGTH_LIMIT:
            return False
        self.length += count
        return True

    def emit(self, code, length=1):
        if self.length + length > LENGTH_LIMIT:
            return False
        self.length += length
        self.code.append(code)
        return True

    def emit_u32(self, x):
        if self.length + 4 > LENGTH_LIMIT:
            return False
        self.length += 4
        self.code.append(x & M32)
        return True

    def emit_random(self):
        return self.emit_u32(self.get_random())

    def execute(self, arg):
        eax = ebx = ecx = edi = 0
        stack = []
        it = iter(self.code)
        immed = 0
        for bc in it:
            if bc & BC_IMMED:
                try:
                    immed = next(it)
                except StopIteration:
                    raise RuntimeError("incomplete immed")
            if bc in (BC_NOP, BC_IMMED):
                pass
            elif bc == BC_MOV_EDI_ARG: edi = arg
            elif bc == BC_PUSH_EBX: stack.append(ebx)
            elif bc == BC_POP_EBX: ebx = stack.pop()
            elif bc == BC_PUSH_ECX: stack.append(ecx)
            elif bc == BC_POP_ECX: ecx = stack.pop()
            elif bc == BC_MOV_EBX_EAX: ebx = eax
            elif bc == BC_MOV_EAX_EDI: eax = edi
            elif bc == BC_MOV_ECX_EBX: ecx = ebx
            elif bc == BC_MOV_EAX_EBX: eax = ebx
            elif bc == BC_AND_ECX_0F: ecx &= 0x0F
            elif bc == BC_SHR_EBX_1: ebx >>= 1
            elif bc == BC_SHL_EAX_1: eax = (eax << 1) & M32
            elif bc == BC_SHR_EAX_CL: eax >>= (ecx & 0x1F)
            elif bc == BC_SHL_EAX_CL: eax = (eax << (ecx & 0x1F)) & M32
            elif bc == BC_OR_EAX_EBX: eax |= ebx
            elif bc == BC_NOT_EAX: eax = (~eax) & M32
            elif bc == BC_NEG_EAX: eax = (-eax) & M32
            elif bc == BC_DEC_EAX: eax = (eax - 1) & M32
            elif bc == BC_INC_EAX: eax = (eax + 1) & M32
            elif bc == BC_ADD_EAX_EBX: eax = (eax + ebx) & M32
            elif bc == BC_SUB_EAX_EBX: eax = (eax - ebx) & M32
            elif bc == BC_IMUL_EAX_EBX: eax = (eax * ebx) & M32
            elif bc == BC_ADD_EAX_IMMED: eax = (eax + immed) & M32
            elif bc == BC_SUB_EAX_IMMED: eax = (eax - immed) & M32
            elif bc == BC_AND_EBX_IMMED: ebx &= immed
            elif bc == BC_AND_EAX_IMMED: eax &= immed
            elif bc == BC_XOR_EAX_IMMED: eax ^= immed
            elif bc == BC_MOV_EAX_IMMED: eax = immed
            elif bc == BC_MOV_EAX_INDIRECT:
                idx = eax
                if idx >= len(CTRL):
                    raise RuntimeError("ctrl index oob")
                eax = (~CTRL[idx]) & M32
            elif bc == BC_RETN:
                if stack:
                    raise RuntimeError("imbalanced stack")
                return eax
            else:
                raise RuntimeError("bad bytecode %d" % bc)
        raise RuntimeError("no retn")


_program_cache = {}


def generate_program(seed):
    # NOTE: GARbro reuses the same program instance on stage fallback,
    # so the RNG state (m_seed) carries over between attempts.
    p = CxProgram(seed)
    for stage in range(5, 0, -1):
        if (p.emit_nop(5) and p.emit(BC_MOV_EDI_ARG, 4)
                and _emit_body(p, stage)
                and p.emit_nop(5) and p.emit(BC_RETN)):
            return p
        p.code = []
        p.length = 0
    raise RuntimeError("overly large cx program")


def _emit_body(p, stage):
    if stage == 1:
        return _emit_prolog(p)
    if not p.emit(BC_PUSH_EBX):
        return False
    if p.get_random() & 1:
        if not _emit_body(p, stage - 1):
            return False
    elif not _emit_body2(p, stage - 1):
        return False
    if not p.emit(BC_MOV_EBX_EAX, 2):
        return False
    if p.get_random() & 1:
        if not _emit_body(p, stage - 1):
            return False
    elif not _emit_body2(p, stage - 1):
        return False
    return _emit_odd(p) and p.emit(BC_POP_EBX)


def _emit_body2(p, stage):
    if stage == 1:
        return _emit_prolog(p)
    if p.get_random() & 1:
        rc = _emit_body(p, stage - 1)
    else:
        rc = _emit_body2(p, stage - 1)
    return rc and _emit_even(p)


def _emit_prolog(p):
    k = PROLOG[p.get_random() % 3]
    if k == 2:
        idx = p.get_random() & 0x3FF
        return (p.emit_nop(5) and p.emit(BC_MOV_EAX_IMMED, 2)
                and p.emit_u32(idx) and p.emit(BC_MOV_EAX_INDIRECT, 0))
    if k == 1:
        return p.emit(BC_MOV_EAX_EDI, 2)
    return p.emit(BC_MOV_EAX_IMMED) and p.emit_random()


def _emit_even(p):
    k = EVEN[p.get_random() & 7]
    if k == 0: return p.emit(BC_NOT_EAX, 2)
    if k == 1: return p.emit(BC_DEC_EAX)
    if k == 2: return p.emit(BC_NEG_EAX, 2)
    if k == 3: return p.emit(BC_INC_EAX)
    if k == 4:
        return (p.emit_nop(5) and p.emit(BC_AND_EAX_IMMED) and p.emit_u32(0x3FF)
                and p.emit(BC_MOV_EAX_INDIRECT, 3))
    if k == 5:
        return (p.emit(BC_PUSH_EBX) and p.emit(BC_MOV_EBX_EAX, 2)
                and p.emit(BC_AND_EBX_IMMED, 2) and p.emit_u32(0xAAAAAAAA)
                and p.emit(BC_AND_EAX_IMMED) and p.emit_u32(0x55555555)
                and p.emit(BC_SHR_EBX_1, 2) and p.emit(BC_SHL_EAX_1, 2)
                and p.emit(BC_OR_EAX_EBX, 2) and p.emit(BC_POP_EBX))
    if k == 6:
        return p.emit(BC_XOR_EAX_IMMED) and p.emit_random()
    op = BC_ADD_EAX_IMMED if (p.get_random() & 1) else BC_SUB_EAX_IMMED
    return p.emit(op) and p.emit_random()


def _emit_odd(p):
    k = ODD[p.get_random() % 6]
    if k == 0:
        return (p.emit(BC_PUSH_ECX) and p.emit(BC_MOV_ECX_EBX, 2)
                and p.emit(BC_AND_ECX_0F, 3) and p.emit(BC_SHR_EAX_CL, 2)
                and p.emit(BC_POP_ECX))
    if k == 1:
        return (p.emit(BC_PUSH_ECX) and p.emit(BC_MOV_ECX_EBX, 2)
                and p.emit(BC_AND_ECX_0F, 3) and p.emit(BC_SHL_EAX_CL, 2)
                and p.emit(BC_POP_ECX))
    if k == 2: return p.emit(BC_ADD_EAX_EBX, 2)
    if k == 3: return p.emit(BC_NEG_EAX, 2) and p.emit(BC_ADD_EAX_EBX, 2)
    if k == 4: return p.emit(BC_IMUL_EAX_EBX, 3)
    return p.emit(BC_SUB_EAX_EBX, 2)


def execute_xcode(key):
    seed = key & 0x7F
    prog = _program_cache.get(seed)
    if prog is None:
        prog = generate_program(seed)
        _program_cache[seed] = prog
    h = key >> 7
    ret1 = prog.execute(h)
    ret2 = prog.execute((~h) & M32)
    return ret1, ret2


def decode(key, buf, lo, hi):
    """In-place CxEncryption decode of buf[lo:hi] (bytearray).

    buf[lo:hi] corresponds to stream offsets [lo, hi); key1/key2 special
    positions are absolute stream offsets.
    """
    ret1, ret2 = execute_xcode(key & M32)
    key1 = ret2 >> 16
    key2 = ret2 & 0xFFFF
    key3 = ret1 & 0xFF
    if key1 == key2:
        key2 = (key2 + 1) & M32
    if key3 == 0:
        key3 = 1
    for i in range(lo, hi):
        buf[i] ^= key3
    for pos, x in ((key2, (ret1 >> 16) & 0xFF), (key1, (ret1 >> 8) & 0xFF)):
        if lo <= pos < hi:
            buf[pos] ^= x


def cx_decrypt_file(data, hash_):
    buf = bytearray(data)
    base = (hash_ & MASK) + OFFSET
    if base < len(buf):
        decode(hash_, buf, 0, base)
        key = ((hash_ >> 16) ^ hash_) & M32
        decode(key, buf, base, len(buf))
    else:
        decode(hash_, buf, 0, len(buf))
    return bytes(buf)


# ---- XP3 TOC parsing ----
def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def u64(b, o): return struct.unpack_from("<Q", b, o)[0]


def read_toc(path):
    with open(path, "rb") as f:
        head = f.read(0x20)
        if head[:11] != MAGIC:
            raise SystemExit("unexpected xp3 signature: %r" % head[:16])
        dir_off = u64(head, 11)
        f.seek(dir_off)
        h = f.read(21)
        if u32(h, 0) == 0x80:
            dir_off = u64(h, 9)
            f.seek(dir_off)
            h = f.read(21)
        htype = h[0]
        if htype == 0:
            f.seek(dir_off + 9)
            toc = f.read(u64(h, 1))
        else:
            f.seek(dir_off + 17)
            toc = zlib.decompress(f.read(u64(h, 1)))
    return toc


def parse_toc(toc):
    entries = []
    sen_refs = []
    pos = 0
    while pos < len(toc):
        sig = u32(toc, pos)
        size = u64(toc, pos + 4)
        body = toc[pos + 12: pos + 12 + size]
        if sig == 0x656C6946:  # File
            e = {}
            p = 0
            while p < len(body):
                ssig = u32(body, p)
                ssize = u64(body, p + 4)
                sbody = body[p + 12: p + 12 + ssize]
                if ssig == 0x6F666E69:  # info
                    e["prot"] = u32(sbody, 0)
                    e["fsize"] = u64(sbody, 4)
                    e["psize"] = u64(sbody, 12)
                    nlen = u16(sbody, 20)
                    e["name"] = sbody[22:22 + nlen * 2].decode("utf-16-le", "replace")
                elif ssig == 0x6D676573:  # segm
                    segs = []
                    for i in range(ssize // 0x1C):
                        o = i * 0x1C
                        segs.append((u32(sbody, o), u64(sbody, o + 4),
                                     u64(sbody, o + 12), u64(sbody, o + 20)))
                    e["segm"] = segs
                elif ssig == 0x726C6461:  # adlr
                    e["hash"] = u32(sbody, 0)
                p += 12 + ssize
            entries.append(e)
        elif (sig >> 24) == 0x3A:  # "sen:" / "yuz:" / "dls:" names section
            if len(body) >= 0x14:
                sen_refs.append((u64(body, 0), u32(body, 16)))
        pos += 12 + size
    return entries, sen_refs


def parse_yuz_names(blob, md5_map, hash_map):
    pos = 0
    while pos < len(blob):
        if pos + 12 > len(blob):
            break
        sig = u32(blob, pos)
        size = u64(blob, pos + 4)
        pos += 12
        if size <= 7 or pos + size > len(blob):
            break
        if sig != 0x656C6946 and (sig >> 24) != 0x3A:
            h = u32(blob, pos)
            nlen = struct.unpack_from("<h", blob, pos + 4)[0]
            if nlen > 0 and nlen * 2 <= size - 6:
                name = blob[pos + 6: pos + 6 + nlen * 2].decode("utf-16-le")
                md5_map[hashlib.md5(name.lower().encode("utf-16-le")).hexdigest()] = name
                hash_map.setdefault(h, name)
        pos += size


def map_name(e, md5_map, hash_map):
    raw = e.get("name", "")
    if raw in md5_map:
        return md5_map[raw]
    if e.get("hash") in hash_map:
        return hash_map[e["hash"]]
    return raw


def extract(archive, outdir, only_ext=None):
    toc = read_toc(archive)
    entries, sen_refs = parse_toc(toc)
    md5_map, hash_map = {}, {}
    with open(archive, "rb") as f:
        for off, size in sen_refs:
            f.seek(off)
            blob = zlib.decompress(f.read(size))
            parse_yuz_names(blob, md5_map, hash_map)
    print("name map: %d md5, %d hash entries; %d file entries" %
          (len(md5_map), len(hash_map), len(entries)))
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for e in entries:
        name = map_name(e, md5_map, hash_map)
        if len(name) > 180 or any(c in name for c in '<>:"|?*'):
            print("skipped decoy entry:", name[:60])
            continue
        if only_ext and not name.lower().endswith(only_ext):
            continue
        comp, off, sz, psz = e["segm"][0]
        with open(archive, "rb") as f:
            f.seek(off)
            raw = f.read(psz)
        if comp:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                print("zlib fail:", name)
                continue
        if e.get("prot", 0) & 0x80000000:
            raw = cx_decrypt_file(raw, e.get("hash", 0))
        if raw[:4] != b"PSB\x00" and name.lower().endswith(".scn"):
            print("WARNING: bad PSB magic:", name, raw[:8].hex())
        outp = os.path.join(outdir, *name.replace("\\", "/").split("/"))
        os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
        with open(outp, "wb") as f:
            f.write(raw)
        n += 1
        print("extracted %s (%d bytes)" % (name, len(raw)))
    print("total extracted:", n)


if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
