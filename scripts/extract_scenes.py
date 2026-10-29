#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render ordered per-scene transcripts (speaker + CN text, narration inline),
grouped into route/chapter folders.

Input : scn_raw/*.ks.scn (+ FreeMote .ks.json when available; 200 uses psb_parser)
Output: transcripts/<章节>/<场景>.md
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SCN_DIR = os.path.join(BASE, "scn_raw")
OUT_DIR = os.path.join(BASE, "transcripts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psb_parser import PsbParser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [
    (r"^0", "01_共通线"),
    (r"^1", "02_芳乃线"),
    (r"^2", "03_茉子线"),
    (r"^3", "04_丛雨线"),
    (r"^4", "05_蕾娜线"),
    (r"^5", "06_小春·芦花线"),
]


def route_of(name):
    for pat, folder in ROUTES:
        if re.match(pat, name):
            return folder
    return "00_其它"


def is_dialogue(o):
    return (
        isinstance(o, list)
        and len(o) >= 4
        and o[1] is None
        and isinstance(o[2], list)
        and len(o[2]) >= 3
        and isinstance(o[2][2], list)
        and len(o[2][2]) >= 2
        and isinstance(o[2][2][1], str)
    )


def walk(obj, out):
    if isinstance(obj, list):
        if is_dialogue(obj):
            out.append(obj)
            return
        for v in obj:
            walk(v, out)
    elif isinstance(obj, dict):
        for v in obj.values():
            walk(v, out)


def get_voice(field):
    if isinstance(field, dict):
        v = field.get("voice")
        return v if isinstance(v, str) else None
    if isinstance(field, list):
        for item in field:
            if isinstance(item, dict):
                v = item.get("voice")
                if isinstance(v, str):
                    return v
    return None


def load_root(scn_path):
    json_path = scn_path[:-4] + ".json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    with open(scn_path, "rb") as f:
        return PsbParser(f.read()).parse()


def main():
    files = sorted(f for f in os.listdir(SCN_DIR) if f.endswith(".ks.scn"))
    jp2cn = {}
    # first pass: build JP->CN speaker map
    for fn in files:
        root = load_root(os.path.join(SCN_DIR, fn))
        found = []
        walk(root, found)
        for e in found:
            jp = e[0] if isinstance(e[0], str) else None
            cn = e[2][2][0] if isinstance(e[2][2][0], str) else None
            if jp and cn:
                jp2cn.setdefault(jp, cn)

    counts = {}
    for fn in files:
        root = load_root(os.path.join(SCN_DIR, fn))
        found = []
        walk(root, found)
        scene = fn[:-7]
        folder = route_of(scene)
        os.makedirs(os.path.join(OUT_DIR, folder), exist_ok=True)
        md = ["# %s" % scene, ""]
        for e in found:
            cn_name, cn_text = e[2][2][0], e[2][2][1]
            jp = e[0] if isinstance(e[0], str) else None
            if isinstance(cn_name, str) and cn_name:
                speaker = cn_name
            elif jp:
                speaker = jp2cn.get(jp, jp)
            else:
                speaker = None
            if speaker:
                md.append("**%s**：%s" % (speaker, cn_text))
            else:
                md.append(cn_text)
        outp = os.path.join(OUT_DIR, folder, scene + ".md")
        with open(outp, "w", encoding="utf-8") as f:
            f.write("\n\n".join(md) + "\n")
        counts[folder] = counts.get(folder, 0) + 1
        print("%-24s <- %s (%d lines)" % (folder, scene, len(found)))
    for k in sorted(counts):
        print(k, counts[k])


if __name__ == "__main__":
    main()
