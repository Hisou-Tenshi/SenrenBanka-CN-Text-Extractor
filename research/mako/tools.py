"""茉子研究辅助工具。只做检索与核对，不做心理判断。

用法（在仓库根目录运行）:
  python research/mako/tools.py scenes [--min 3]          列出茉子出场的场景块（自动排除保留集）
  python research/mako/tools.py grep 正则 [--speaker 茉子] [--ctx 6] [--files 2,3] [--max 40]
  python research/mako/tools.py show 205 943 961           打印指定行范围（保留集会被拒绝）
  python research/mako/tools.py refs 报告.md               核对报告中的 文件编号:行号 引用
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "transcripts"
HOLDOUT = {"013", "111", "310", "420"}
SPEAKER_RE = re.compile(r"^\*\*(.+?)\*\*：")
REF_RE = re.compile(r"(?<![\d.])(\d{3}[ab]?):(\d+)(?:[–-](\d+))?")

sys.stdout.reconfigure(encoding="utf-8")


def file_id(p: Path) -> str:
    m = re.match(r"(\d{3}[ab]?)", p.name)
    return m.group(1) if m else p.stem


def load():
    """返回 {文件编号: (路线目录, 行列表)}，行号从 1 开始对应 lines[i-1]。"""
    out = {}
    for p in sorted(ROOT.rglob("*.md")):
        out[file_id(p)] = (p.parent.name, p.read_text(encoding="utf-8").splitlines())
    return out


def speaker(line: str):
    m = SPEAKER_RE.match(line)
    return m.group(1) if m else None


def cmd_scenes(a):
    """茉子发言间隔不超过 gap 行的连续区段视为一个场景块。"""
    for fid, (route, lines) in load().items():
        if fid in HOLDOUT:
            continue
        idx = [i + 1 for i, l in enumerate(lines) if (s := speaker(l)) and "茉子" in s and "母亲" not in s]
        if not idx:
            continue
        start = prev = idx[0]
        count = 1
        for n in idx[1:] + [None]:
            if n is not None and n - prev <= a.gap:
                prev, count = n, count + 1
                continue
            if count >= a.min:
                who = {speaker(l) for l in lines[start - 1:prev] if speaker(l)} - {None}
                print(f"{fid}:{start}-{prev}\t{route}\t茉子{count}句\t{'、'.join(sorted(who))}")
            if n is not None:
                start = prev = n
                count = 1


def cmd_grep(a):
    rx = re.compile(a.pattern)
    allow = set(a.files.split(",")) if a.files else None
    hits = 0
    for fid, (route, lines) in load().items():
        if fid in HOLDOUT or (allow and not any(fid.startswith(x) for x in allow)):
            continue
        for i, l in enumerate(lines, 1):
            if not rx.search(l):
                continue
            if a.speaker and not ((s := speaker(l)) and a.speaker in s):
                continue
            lo, hi = max(1, i - a.ctx), min(len(lines), i + a.ctx)
            print(f"== {fid}:{i} ({route})")
            for j in range(lo, hi + 1):
                if lines[j - 1].strip():
                    print(f"{'>' if j == i else ' '}{j}\t{lines[j - 1]}")
            hits += 1
            if hits >= a.max:
                print(f"[已达上限 {a.max}]")
                return


def cmd_show(a):
    if a.fid in HOLDOUT:
        sys.exit(f"{a.fid} 属于保留集，拒绝显示")
    route, lines = load()[a.fid]
    print(f"== {a.fid} ({route}) {a.start}-{a.end}")
    for j in range(a.start, min(a.end, len(lines)) + 1):
        if lines[j - 1].strip():
            print(f"{j}\t{lines[j - 1]}")


def cmd_refs(a):
    data = load()
    text = Path(a.report).read_text(encoding="utf-8")
    refs = sorted({(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in REF_RE.finditer(text)})
    bad = 0
    for fid, s, e in refs:
        if fid not in data:
            print(f"MISSING-FILE  {fid}:{s}"); bad += 1; continue
        n = len(data[fid][1])
        if s < 1 or e < s or e > n:
            print(f"OUT-OF-RANGE  {fid}:{s}-{e} (文件共 {n} 行)"); bad += 1
        elif s == e and not data[fid][1][s - 1].strip():
            print(f"BLANK-LINE    {fid}:{s}"); bad += 1
        if fid in HOLDOUT:
            print(f"HOLDOUT       {fid}:{s}-{e}"); bad += 1
    print(f"checked {len(refs)} refs, {bad} issues")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scenes"); s.add_argument("--min", type=int, default=3); s.add_argument("--gap", type=int, default=30)
    g = sub.add_parser("grep"); g.add_argument("pattern"); g.add_argument("--speaker"); g.add_argument("--ctx", type=int, default=6)
    g.add_argument("--files"); g.add_argument("--max", type=int, default=40)
    sh = sub.add_parser("show"); sh.add_argument("fid"); sh.add_argument("start", type=int); sh.add_argument("end", type=int)
    r = sub.add_parser("refs"); r.add_argument("report")
    a = ap.parse_args()
    {"scenes": cmd_scenes, "grep": cmd_grep, "show": cmd_show, "refs": cmd_refs}[a.cmd](a)


if __name__ == "__main__":
    main()
