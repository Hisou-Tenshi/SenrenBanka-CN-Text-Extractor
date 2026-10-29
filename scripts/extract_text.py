#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract Simplified-Chinese character dialogue from Senren Banka scn JSONs.
Input : scn_raw/*.ks.scn (+ FreeMote .ks.json when available; 200 uses psb_parser)
Output: characters/<角色名>.json  — one file per character
        narration.json            — lines without a speaker
        _summary.json             — statistics
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psb_parser import PsbParser

SCN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scn_raw")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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
    """Collect dialogues in document order."""
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
        data = f.read()
    return PsbParser(data).parse()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SCN_DIR) if f.endswith(".ks.scn"))
    print("scene files:", len(files))

    chars = {}          # name -> list of line dicts
    narration = []
    jp2cn = {}          # map JP speaker name -> CN speaker name
    total = 0

    for fn in files:
        scn_path = os.path.join(SCN_DIR, fn)
        root = load_root(scn_path)
        found = []
        walk(root, found)
        scene = fn[:-7]  # strip .ks.scn
        for e in found:
            langs = e[2]
            cn_pair = langs[2]
            cn_name, cn_text = cn_pair[0], cn_pair[1]
            jp_name = e[0] if isinstance(e[0], str) else None
            if isinstance(cn_name, str) and cn_name and isinstance(jp_name, str) and jp_name:
                jp2cn.setdefault(jp_name, cn_name)
            speaker = cn_name if isinstance(cn_name, str) and cn_name else jp_name
            voice = get_voice(e[3])
            entry = {"file": scene, "text": cn_text}
            if voice:
                entry["voice"] = voice
            total += 1
            if speaker:
                if isinstance(cn_name, str) and cn_name:
                    speaker = cn_name
                elif jp_name:
                    speaker = jp2cn.get(jp_name, jp_name)
                chars.setdefault(speaker, []).append(entry)
            else:
                narration.append(entry)
        print("%-40s dialogues: %d" % (fn, len(found)))

    # write per-character files
    index = {}
    for name, lines in sorted(chars.items(), key=lambda kv: -len(kv[1])):
        outp = os.path.join(OUT_DIR, name + ".json")
        with open(outp, "w", encoding="utf-8") as f:
            json.dump({"character": name, "count": len(lines), "lines": lines},
                      f, ensure_ascii=False, indent=1)
        index[name] = len(lines)

    with open(os.path.join(OUT_DIR, "narration.json"), "w", encoding="utf-8") as f:
        json.dump({"character": "旁白（无说话人）", "count": len(narration), "lines": narration},
                  f, ensure_ascii=False, indent=1)

    summary = {
        "game": "千恋＊万花 - Senren Banka (Steam CN)",
        "source": "scn.xp3 (.ks.scn scripts, 简体中文轨)",
        "total_dialogue_entries": total,
        "total_characters": len(chars),
        "characters": dict(sorted(index.items(), key=lambda kv: -kv[1])),
        "narration_lines": len(narration),
    }
    with open(os.path.join(OUT_DIR, "_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("total dialogues:", total, "characters:", len(chars), "narration:", len(narration))


if __name__ == "__main__":
    main()
