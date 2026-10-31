"""23 号语气研究的语料整理与描述性统计工具。只提取客观特征，不判断"像不像茉子"。

用法（在仓库根目录运行）:
  python research/mako/voice.py build                 生成 23_corpus.jsonl（茉子每条台词 + 元数据 + 日文）
  python research/mako/voice.py stats                 打印分段描述统计（输出到 23_stats.txt 时用重定向）
  python research/mako/voice.py ctx 205 1909 [--before 12 --after 8] [--nojp]
                                                      显示剧本上下文，茉子台词下附日文原文
  python research/mako/voice.py find 正则 [--seg Mpost] [--jp] [--max 40] [--ctx 0]
                                                      检索茉子台词（--jp 表示对日文检索）
  python research/mako/voice.py refs 报告.md          核对引用存在性，并标出落入验证保留段的引用

对齐方式：剧本 md 中 **茉子** 台词的顺序与 data/characters/茉子.json 逐文件完全一致（86/86 文件已核对），
中文与日文 JSON 以 voice 编号一一对应（3409/3409）。因此每条台词都能定位到剧本行号并附上日文。

分段（segment）:
  C      共通线 001–015
  Mpre   茉子线 200 至 205:1984（交往前）
  Mpost  茉子线 205:1985 起至 210（交往后；205:1985 为接吻、确认关系处）
  Y R L S 芳乃线 / 丛雨线 / 蕾娜线 / 小春・芦花线
对话对象（addr）是启发式的：取茉子该句前后各最近 3 个他人发言（同一场景块内，间隔不超过 20 行），
只有一位他人时记为该人，多于一位记为"多人"，没有时记为"?"。这只用于粗分，不能代替读原文。
验证保留段（VALIDATION）在质性分析阶段不得阅读，ctx 会拒绝显示，stats 和 find 会排除。
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[2]
TR = REPO / "data" / "transcripts"
CN = REPO / "data" / "characters" / "茉子.json"
JP = REPO / "data" / "characters_jp" / "茉子.json"
OUT = Path(__file__).resolve().parent / "23_corpus.jsonl"
SPK = re.compile(r"^\*\*(.+?)\*\*：(.*)$")
RUBY = re.compile(r"\[[^\]]*\]")

# 第七阶段的验证保留段：在质性分析开始前固定，分析者不得阅读。 (文件编号, 起始行, 结束行)
VALIDATION = [
    # 只按"行号窗口 × 说话人分布"选定，选定时没有读过窗口内容。
    ("208", 751, 1049),   # 交往后：含芳乃/安晴等在场的家中段 + 二人段
    ("210", 151, 401),    # 交往后：尾声二人段
    ("203", 301, 600),    # 交往前：茉子线，主要对将臣
    ("010", 151, 450),    # 共通线：多人日常（芳乃、蕾娜、丛雨在场）
]


def held(fid, line):
    return any(f == fid and s <= line <= e for f, s, e in VALIDATION)


def fid_of(name):
    m = re.match(r"(\d{3}[ab]?)", name)
    return m.group(1)


def segment(fid, line):
    n = int(fid[:3])
    if n < 100:
        return "C"
    if 200 <= n < 300:
        if n < 205 or (n == 205 and line < 1985):
            return "Mpre"
        return "Mpost"
    return {1: "Y", 3: "R", 4: "L", 5: "S"}[n // 100]


def load_transcripts():
    out = {}
    for p in sorted(TR.rglob("*.md")):
        out[fid_of(p.name)] = (p.stem, p.read_text(encoding="utf-8").splitlines())
    return out


def jp_clean(s):
    return RUBY.sub("", s).replace("\u3000", " ")


def build_rows():
    tr = load_transcripts()
    cn = json.loads(CN.read_text(encoding="utf-8"))["lines"]
    jp = json.loads(JP.read_text(encoding="utf-8"))["lines"]
    assert len(cn) == len(jp) and all(a["voice"] == b["voice"] for a, b in zip(cn, jp))
    by_file = defaultdict(list)
    for a, b in zip(cn, jp):
        by_file[a["file"]].append((a, b))
    rows = []
    for fid, (stem, lines) in tr.items():
        pairs = by_file.get(stem, [])
        spk = [(i + 1, m.group(1), m.group(2)) for i, l in enumerate(lines) if (m := SPK.match(l))]
        mk = [x for x in spk if x[1] == "茉子"]
        assert len(mk) == len(pairs), stem
        for (ln, _, text), (a, b) in zip(mk, pairs):
            assert text == a["text"], (stem, ln)
            # 启发式对象：同块内前后最近 3 个他人发言
            others = []
            for direction in (-1, 1):
                got, last = 0, ln
                seq = [x for x in spk if (x[0] < ln if direction < 0 else x[0] > ln)]
                if direction < 0:
                    seq = seq[::-1]
                for l2, s2, _ in seq:
                    if abs(l2 - last) > 20 or got >= 3:
                        break
                    last = l2
                    if s2 != "茉子":
                        others.append(s2)
                        got += 1
            names = set()
            for o in others:
                names.update(o.split("・"))
            names.discard("茉子")
            addr = next(iter(names)) if len(names) == 1 else ("多人" if names else "?")
            prev = next((x for x in reversed(spk) if x[0] < ln), None)
            rows.append({
                "fid": fid, "line": ln, "seg": segment(fid, ln), "addr": addr,
                "prev_spk": prev[1] if prev else None, "voice": a["voice"],
                "cn": text, "jp": jp_clean(b["text"]), "held": held(fid, ln),
            })
    cnt = Counter(r["cn"] for r in rows)
    for r in rows:
        r["dup"] = cnt[r["cn"]]
    return rows


def load_rows():
    if not OUT.exists():
        sys.exit("先运行 build")
    return [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines()]


def cmd_build(a):
    rows = build_rows()
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(rows)} rows, held-out {sum(r['held'] for r in rows)}")


# ---------- 统计 ----------
QUOTE = re.compile(r"^「|」$")
SENT_SPLIT = re.compile(r"(?<=[。！？!?…])(?=[^。！？!?…」])")
PUNCT = re.compile(r"[，。、！？!?…—～~「」『』（）()\s·“”]")


def body(s):
    return QUOTE.sub("", s)


def sentences(s):
    return [x for x in SENT_SPLIT.split(body(s)) if PUNCT.sub("", x)]


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "-"


def cmd_stats(a):
    rows = [r for r in load_rows() if not r["held"]]
    segs = ["Mpost", "Mpre", "C", "Y", "R", "L", "S"]
    by = defaultdict(list)
    for r in rows:
        by[r["seg"]].append(r)
    print("# 23 号描述统计（已排除验证保留段）。只用于定位现象，不是生成参数。\n")
    print("## 1 规模与对象（启发式）")
    for s in segs:
        rs = by[s]
        ad = Counter(r["addr"] for r in rs).most_common(5)
        print(f"{s:6} n={len(rs):4}  对象: " + "、".join(f"{k}{v}" for k, v in ad))

    print("\n## 2 长度与结构（字数不计标点）")
    print("seg     中位字数  ≤5字  ≥25字  多句  纯沉默(……)  含…  含！  含？  含～  含——")
    for s in segs:
        rs = by[s]
        if not rs:
            continue
        L = sorted(len(PUNCT.sub("", body(r["cn"]))) for r in rs)
        n = len(rs)
        f = lambda ch: pct(sum(ch in r["cn"] for r in rs), n)
        print(f"{s:6} {L[n // 2]:6}   {pct(sum(x <= 5 for x in L), n):>5} {pct(sum(x >= 25 for x in L), n):>5}"
              f" {pct(sum(len(sentences(r['cn'])) > 1 for r in rs), n):>5} {pct(sum(x == 0 for x in L), n):>8}"
              f"   {f('…'):>4} {f('！'):>4} {f('？'):>4} {f('～'):>4} {f('—'):>4}")

    print("\n## 3 连续发言（茉子连续说几条才轮到别人）")
    tr = load_transcripts()
    runs = defaultdict(Counter)
    for fid, (_, lines) in tr.items():
        cur = 0
        segcur = None
        for i, l in enumerate(lines, 1):
            m = SPK.match(l)
            if not m:
                continue
            if m.group(1) == "茉子" and not held(fid, i):
                cur += 1
                segcur = segment(fid, i)
            else:
                if cur:
                    runs[segcur][min(cur, 5)] += 1
                cur = 0
        if cur:
            runs[segcur][min(cur, 5)] += 1
    for s in segs:
        c = runs[s]
        t = sum(c.values())
        if t:
            print(f"{s:6} 轮次={t:4}  " + "  ".join(f"{k if k < 5 else '5+'}条:{pct(c[k], t)}" for k in range(1, 6)))

    print("\n## 4 称呼与自称（中文，按句计）")
    terms = ["有地", "将臣", "少爷", "有地先生", "您", "你", "芳乃大人", "芳乃", "安晴大人", "丛雨大人", "蕾娜",
             "小春", "芦花", "我", "人家", "茉子"]
    print("seg    " + " ".join(f"{t:>5}" for t in terms))
    for s in segs:
        rs = by[s]
        if rs:
            print(f"{s:6} " + " ".join(f"{pct(sum(t in r['cn'] for r in rs), len(rs)):>5}" for t in terms))

    print("\n## 5 日文：自称、称呼、文体（按句计）")
    jterms = ["ワタシ", "私", "有地さん", "将臣さん", "将臣", "芳乃様", "安晴様", "ムラサメ様", "です", "ます",
              "ません", "でした", "ください", "だよ", "だね", "じゃない", "かな", "なぁ", "ねぇ", "ニンニン", "ふふ", "むふ"]
    print("seg    " + " ".join(f"{t:>5}" for t in jterms))
    for s in segs:
        rs = by[s]
        if rs:
            print(f"{s:6} " + " ".join(f"{pct(sum(t in r['jp'] for r in rs), len(rs)):>5}" for t in jterms))

    print("\n## 6 日文句末文体（只看最后一句，去掉标点）——敬体/常体粗分")
    end_rx = re.compile(r"[「」。、！？!?…―ー～~\s♪]+$")
    polite = re.compile(r"(です|ます|ません|でした|ましょう|ください|ませ)(よ|ね|よね|か|かね|な|ねぇ|よぉ|って|けど|から|が)?$")
    for s in segs:
        rs = by[s]
        if not rs:
            continue
        c = Counter()
        for r in rs:
            t = end_rx.sub("", r["jp"])
            if len(t) < 3:
                c["极短/无"] += 1
            elif polite.search(t):
                c["敬体"] += 1
            else:
                c["其他"] += 1
        n = len(rs)
        print(f"{s:6} 敬体 {pct(c['敬体'], n):>4}  其他 {pct(c['其他'], n):>4}  极短 {pct(c['极短/无'], n):>4}")
    # 分对象：Mpost/Mpre/C 中对将臣单独对话 vs 其他
    print("  按对象（仅单一对象可判定的句子）:")
    for s in ["C", "Mpre", "Mpost", "Y", "R", "L"]:
        for who in ["将臣", "芳乃", "安晴", "丛雨", "蕾娜"]:
            rs = [r for r in by[s] if r["addr"] == who and len(end_rx.sub("", r["jp"])) >= 3]
            if len(rs) >= 15:
                k = sum(bool(polite.search(end_rx.sub("", r["jp"]))) for r in rs)
                print(f"  {s:6} 对{who:3} n={len(rs):4} 敬体 {pct(k, len(rs))}")

    print("\n## 7 中文句首（前 2 字，含语气词）与句尾（末 1 字）top 12")
    for s in ["Mpost", "Mpre", "C"]:
        rs = [r for r in by[s] if PUNCT.sub("", body(r["cn"]))]
        h = Counter(PUNCT.sub("", body(r["cn"]))[:2] for r in rs).most_common(12)
        t = Counter(re.sub(r"[」…。！？，～—\s]+$", "", body(r["cn"]))[-1:] for r in rs).most_common(12)
        print(f"{s:6} 首: " + " ".join(f"{k}{v}" for k, v in h))
        print(f"{'':6} 尾: " + " ".join(f"{k}{v}" for k, v in t))

    print("\n## 8 重复台词（字数≥6 且出现≥2 次）")
    seen = Counter(r["cn"] for r in rows if len(PUNCT.sub("", body(r["cn"]))) >= 6)
    for k, v in seen.most_common():
        if v < 2:
            break
        print(f"  {v}× {k}")


def cmd_ctx(a):
    tr = load_transcripts()
    stem, lines = tr[a.fid]
    lo, hi = max(1, a.line - a.before), min(len(lines), a.line + a.after)
    if any(held(a.fid, j) for j in range(lo, hi + 1)) and not a.unseal:
        sys.exit(f"{a.fid}:{lo}-{hi} 与验证保留段重叠，拒绝显示")
    jp = {(r["fid"], r["line"]): r["jp"] for r in load_rows()}
    print(f"== {a.fid} {stem} {lo}-{hi} [{segment(a.fid, a.line)}]")
    for j in range(lo, hi + 1):
        l = lines[j - 1]
        if not l.strip():
            continue
        print(f"{'>' if j == a.line else ' '}{j}\t{l}")
        if not a.nojp and (a.fid, j) in jp:
            print(f"\t    JP {jp[(a.fid, j)]}")


def cmd_find(a):
    rx = re.compile(a.pattern)
    rows = [r for r in load_rows() if not r["held"] and (not a.seg or r["seg"] in a.seg.split(","))]
    n = 0
    for r in rows:
        if rx.search(r["jp"] if a.jp else r["cn"]):
            print(f"{r['fid']}:{r['line']}\t[{r['seg']}/{r['addr']}]\t{r['cn']}\n\t\tJP {r['jp']}")
            n += 1
            if n >= a.max:
                print(f"[已达上限 {a.max}]")
                break
    print(f"命中 {n}（范围内共 {len(rows)} 条）")


def cmd_refs(a):
    """核对报告中的 文件编号:行号 引用：是否存在、是否落在验证保留段内。"""
    tr = load_transcripts()
    rx = re.compile(r"(?<![\d.])(\d{3}[ab]?):(\d+)(?:[–-](\d+))?")
    text = Path(a.report).read_text(encoding="utf-8")
    refs = sorted({(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in rx.finditer(text)})
    bad = 0
    for fid, s, e in refs:
        if fid not in tr:
            print(f"MISSING-FILE  {fid}:{s}"); bad += 1; continue
        n = len(tr[fid][1])
        if s < 1 or e < s or e > n:
            print(f"OUT-OF-RANGE  {fid}:{s}-{e} (共 {n} 行)"); bad += 1; continue
        if s == e and not tr[fid][1][s - 1].strip():
            print(f"BLANK-LINE    {fid}:{s}"); bad += 1
        if any(held(fid, j) for j in range(s, e + 1)):
            print(f"VALIDATION    {fid}:{s}-{e}"); bad += 1
    print(f"checked {len(refs)} refs, {bad} issues")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("stats")
    c = sub.add_parser("ctx"); c.add_argument("fid"); c.add_argument("line", type=int)
    c.add_argument("--before", type=int, default=12); c.add_argument("--after", type=int, default=8)
    c.add_argument("--nojp", action="store_true"); c.add_argument("--unseal", action="store_true")
    f = sub.add_parser("find"); f.add_argument("pattern"); f.add_argument("--seg"); f.add_argument("--jp", action="store_true")
    f.add_argument("--max", type=int, default=40)
    r = sub.add_parser("refs"); r.add_argument("report")
    a = ap.parse_args()
    {"build": cmd_build, "stats": cmd_stats, "ctx": cmd_ctx, "find": cmd_find, "refs": cmd_refs}[a.cmd](a)


if __name__ == "__main__":
    main()
