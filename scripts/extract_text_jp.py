#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Same as extract_text.py but for the ORIGINAL JAPANESE track (index 0),
for cross-referencing translation choices against the CN output.
Output: characters_jp/<話者名>.json + narration_jp.json + _summary.json
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SCN_DIR = os.path.join(BASE, "scn_raw")
OUT_DIR = os.path.join(BASE, "characters_jp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psb_parser import PsbParser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANG = 0  # 0=日本語 1=English 2=简体中文 3=繁體中文


def is_dialogue(o):
    return (
        isinstance(o, list)
        and len(o) >= 4
        and o[1] is None
        and isinstance(o[2], list)
        and len(o[2]) > LANG
        and isinstance(o[2][LANG], list)
        and len(o[2][LANG]) >= 2
        and isinstance(o[2][LANG][1], str)
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
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SCN_DIR) if f.endswith(".ks.scn"))
    chars = {}
    narration = []
    total = 0
    for fn in files:
        root = load_root(os.path.join(SCN_DIR, fn))
        found = []
        walk(root, found)
        scene = fn[:-7]
        for e in found:
            pair = e[2][LANG]
            speaker = e[0] if isinstance(e[0], str) else None
            voice = get_voice(e[3])
            entry = {"file": scene, "text": pair[1]}
            if voice:
                entry["voice"] = voice
            total += 1
            if speaker:
                chars.setdefault(speaker, []).append(entry)
            else:
                narration.append(entry)
        print("%-40s dialogues: %d" % (fn, len(found)))

    index = {}
    for name, lines in sorted(chars.items(), key=lambda kv: -len(kv[1])):
        with open(os.path.join(OUT_DIR, name + ".json"), "w", encoding="utf-8") as f:
            json.dump({"character": name, "count": len(lines), "lines": lines},
                      f, ensure_ascii=False, indent=1)
        index[name] = len(lines)

    with open(os.path.join(OUT_DIR, "narration_jp.json"), "w", encoding="utf-8") as f:
        json.dump({"character": "なし（語り手なし）", "count": len(narration), "lines": narration},
                  f, ensure_ascii=False, indent=1)
    summary = {
        "language": "日本語（原文）",
        "total_dialogue_entries": total,
        "total_characters": len(chars),
        "characters": dict(sorted(index.items(), key=lambda kv: -kv[1])),
        "narration_lines": len(narration),
    }
    with open(os.path.join(OUT_DIR, "_summary_jp.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("total:", total, "characters:", len(chars), "narration:", len(narration))


if __name__ == "__main__":
    main()
