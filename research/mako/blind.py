"""P3 盲测工具。只用于保留集 013/111/310/420。

规则在代码中固定，运行前不看文本：
- 检查点选择：茉子发言块（相邻茉子台词间隔 <= 30 行）中，按茉子台词数取前 3 块，
  且各检查点相距 >= 100 行；检查点 = 块内茉子第一句台词的行号。
- 情境窗口：检查点之前 60 行。窗口中所有茉子台词、以及疑似茉子视角的旁白
  （非对白且含"有地"或"芳乃大人"）一律遮蔽。
- 结果窗口：检查点起 40 行（不超过块末）。
- reveal 只有在预测文件已写入 seal 日志、且文件当前哈希与日志一致时才输出。

用法（仓库根目录）:
  python research/mako/blind.py layout              各文件的检查点与块结构（无正文）
  python research/mako/blind.py context 111         打印检查点前情境（已遮蔽）
  python research/mako/blind.py seal 预测文件.md     记录哈希并设为只读
  python research/mako/blind.py reveal 111 预测文件.md
"""
import hashlib
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / "data" / "transcripts"
LOG = HERE / "06_blind_access_log.txt"
HOLDOUT = ["013", "111", "310", "420"]
GAP, TOP_K, MIN_DIST, CTX, OUT = 30, 3, 100, 60, 40
SPEAKER_RE = re.compile(r"^\*\*(.+?)\*\*：")
sys.stdout.reconfigure(encoding="utf-8")


def log(msg: str):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{msg}\n")


def lines_of(fid: str):
    p = next(p for p in ROOT.rglob("*.md") if p.name.startswith(fid))
    return p.name, p.read_text(encoding="utf-8").splitlines()


def is_mako(line: str) -> bool:
    m = SPEAKER_RE.match(line)
    return bool(m and "茉子" in m.group(1) and "母亲" not in m.group(1))


def blocks(lines):
    idx = [i + 1 for i, l in enumerate(lines) if is_mako(l)]
    out, start, prev, n = [], None, None, 0
    for x in idx + [None]:
        if x is not None and prev is not None and x - prev <= GAP:
            prev, n = x, n + 1
            continue
        if start is not None:
            out.append((start, prev, n))
        if x is not None:
            start = prev = x
            n = 1
    return out


def checkpoints(lines):
    chosen = []
    for s, e, n in sorted(blocks(lines), key=lambda b: (-b[2], b[0])):
        if all(abs(s - c[0]) >= MIN_DIST for c in chosen):
            chosen.append((s, e, n))
        if len(chosen) == TOP_K:
            break
    return sorted(chosen)


def masked(line: str) -> str:
    if is_mako(line):
        return "**茉子**：[已遮蔽]"
    if not SPEAKER_RE.match(line) and ("有地" in line or "芳乃大人" in line):
        return "[疑似茉子视角旁白，已遮蔽]"
    return line


def cmd_layout():
    for fid in HOLDOUT:
        name, lines = lines_of(fid)
        print(f"== {fid} {name} 共 {len(lines)} 行；茉子块 {len(blocks(lines))} 个")
        for k, (s, e, n) in enumerate(checkpoints(lines), 1):
            print(f"  CP{k}: 检查点 {fid}:{s}，块 {s}-{e}，茉子 {n} 句；情境 {max(1, s - CTX)}-{s - 1}；结果 {s}-{min(e, s + OUT)}")
    log("layout")


def cmd_context(fid: str):
    name, lines = lines_of(fid)
    for k, (s, e, n) in enumerate(checkpoints(lines), 1):
        lo = max(1, s - CTX)
        print(f"\n===== {fid} CP{k} 情境 {lo}-{s - 1}（检查点 {s}）=====")
        for j in range(lo, s):
            if lines[j - 1].strip():
                print(f"{j}\t{masked(lines[j - 1])}")
    log(f"context {fid}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cmd_seal(pred: str):
    p = Path(pred).resolve()
    h = sha(p)
    os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    log(f"seal {p.name} sha256={h}")
    print(f"sealed {p.name} sha256={h}")


def cmd_reveal(fid: str, pred: str):
    p = Path(pred).resolve()
    h = sha(p)
    if f"seal {p.name} sha256={h}" not in (LOG.read_text(encoding="utf-8") if LOG.exists() else ""):
        sys.exit("预测文件未封存或已被修改，拒绝揭盲")
    name, lines = lines_of(fid)
    for k, (s, e, n) in enumerate(checkpoints(lines), 1):
        hi = min(e, s + OUT)
        print(f"\n===== {fid} CP{k} 结果 {s}-{hi} =====")
        for j in range(s, hi + 1):
            if lines[j - 1].strip():
                print(f"{j}\t{lines[j - 1]}")
    log(f"reveal {fid} with {p.name} sha256={h}")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    {"layout": cmd_layout, "context": cmd_context, "seal": cmd_seal, "reveal": cmd_reveal}[cmd](*rest)
