#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal PSB (v2/v3) parser ported from FreeMote.Psb semantics.
Produces plain Python objects (dict/list/int/float/str/bytes)."""
import struct


def _uint(b, o, w):
    if w == 0:
        return 0
    return int.from_bytes(b[o:o + w], "little")


class PsbParser:
    def __init__(self, data, encoding="utf-8"):
        self.data = data
        assert data[:4] == b"PSB\x00", "bad signature"
        self.version = struct.unpack_from("<H", data, 4)[0]
        # @8 header_len, @12 names, @16 strings, @20 strings_data,
        # @24 chunk_offsets, @28 chunk_lengths, @32 chunk_data, @36 entries
        (self.header_len, self.offset_names, self.offset_strings,
         self.offset_strings_data, self.offset_chunk_offsets,
         self.offset_chunk_lengths, self.offset_chunk_data,
         self.offset_entries) = struct.unpack_from("<8I", data, 8)
        self.encoding = encoding
        self._load_names()
        self._load_strings()
        self._load_chunks()

    # ---- primitives ----
    def _read_array(self, pos):
        """Returns (values, end_pos) for an inline PsbArray at pos."""
        d = self.data
        w = d[pos] - 0x0D + 1
        if not 1 <= w <= 8:
            raise ValueError("bad array width %d at %d" % (w, pos))
        count = _uint(d, pos + 1, w)
        ep = pos + 1 + w
        entry_type = d[ep]
        ew = entry_type - 0x0C
        if not 0 <= ew <= 8:
            raise ValueError("bad entry width %d at %d" % (ew, ep))
        ep += 1
        vals = [_uint(d, ep + i * ew, ew) for i in range(count)]
        return vals, ep + ew * count

    def _load_names(self):
        d = self.data
        pos = self.offset_names
        charset, p1 = self._read_array(pos)
        names_data, p2 = self._read_array(p1)
        name_idx, _ = self._read_array(p2)
        nd = names_data  # list of bytes
        names = []
        for index in name_idx:
            out = []
            chr_ = nd[index]
            while chr_ != 0:
                code = nd[chr_]
                out.append(chr_ - charset[code])
                chr_ = code
            out.reverse()
            names.append(bytes(out).decode("utf-8"))
        self.names = names

    def _load_strings(self):
        d = self.data
        offs, _ = self._read_array(self.offset_strings)
        base = self.offset_strings_data
        strings = []
        for o in offs:
            start = base + o
            end = d.index(0, start)
            strings.append(d[start:end].decode(self.encoding))
        self.strings = strings

    def _load_chunks(self):
        d = self.data
        coffs, _ = self._read_array(self.offset_chunk_offsets)
        clens, _ = self._read_array(self.offset_chunk_lengths)
        self.chunks = [d[self.offset_chunk_data + o: self.offset_chunk_data + o + l]
                       for o, l in zip(coffs, clens)]

    # ---- tree ----
    def _unpack(self, pos):
        """Returns (value, end_pos)."""
        d = self.data
        t = d[pos]
        if t == 0x00:
            return None, pos + 1
        if t == 0x01:
            return None, pos + 1
        if t == 0x02:
            return False, pos + 1
        if t == 0x03:
            return True, pos + 1
        if 0x04 <= t <= 0x0C:  # NumberN0..N8
            w = t - 0x04
            return _uint(d, pos + 1, w), pos + 1 + w
        if 0x0D <= t <= 0x14:  # Array (inline, raw uints)
            vals, end = self._read_array(pos)
            return vals, end
        if 0x15 <= t <= 0x18:  # StringN1..N4
            w = t - 0x15 + 1
            idx = _uint(d, pos + 1, w)
            return self.strings[idx], pos + 1 + w
        if 0x19 <= t <= 0x1C:  # ResourceN1..N4
            w = t - 0x19 + 1
            idx = _uint(d, pos + 1, w)
            return {"@res": idx, "len": len(self.chunks[idx])}, pos + 1 + w
        if t == 0x1D:
            return 0.0, pos + 1
        if t == 0x1E:
            return struct.unpack_from("<f", d, pos + 1)[0], pos + 5
        if t == 0x1F:
            return struct.unpack_from("<d", d, pos + 1)[0], pos + 9
        if t == 0x20:  # List
            offs, after = self._read_array(pos + 1)
            lst = []
            for o in offs:
                v, _ = self._unpack(after + o)
                lst.append(v)
            # end pos: max(offset + parsed size); approximate by parsing last
            # element fully to learn the end
            if offs:
                _, end = self._unpack(after + offs[-1])
            else:
                end = after
            return lst, end
        if t == 0x21:  # Objects
            name_idx, p1 = self._read_array(pos + 1)
            offs, after = self._read_array(p1)
            obj = {}
            end = after
            for i, ni in enumerate(name_idx):
                name = self.names[ni]
                v, vend = self._unpack(after + offs[i])
                obj[name] = v
                end = max(end, vend)
            return obj, end
        if 0x22 <= t <= 0x25:  # ExtraChunkN1..N4 (v4)
            w = t - 0x22 + 1
            idx = _uint(d, pos + 1, w)
            return {"@extra": idx}, pos + 1 + w
        raise ValueError("unknown type 0x%02X at %d" % (t, pos))

    def parse(self):
        root, _ = self._unpack(self.offset_entries)
        return root


if __name__ == "__main__":
    import json, sys
    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()
    p = PsbParser(data)
    obj = p.parse()
    out = json.dumps(obj, ensure_ascii=False, indent=1, default=repr)
    with open(sys.argv[2] if len(sys.argv) > 2 else path + ".py.json", "w", encoding="utf-8") as f:
        f.write(out)
    print("parsed OK; root keys:", list(obj.keys())[:20] if isinstance(obj, dict) else type(obj))
