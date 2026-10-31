> [!WARNING]
> **⚠️ 超级叠甲免责声明 · 使用前必读（SUPER DISCLAIMER）**
>
> **本项目是个人、非官方、非商业性质的技术研究与学习项目，与 Yuzusoft、NekoNyan、Hikari Field、Steam 及任何游戏权利方均无隶属、合作、授权或背书关系。**
>
> - **仅供学习**：仅用于研究 KiriKiri Z 引擎、XP3 封包、cxdec 加密、PSB 格式与文本处理；**不提供游戏本体、破解补丁、汉化补丁**，也不提供任何可运行的"学习版"。
> - **版权归属**：游戏文本、角色、剧本、语音、商标等一切内容版权归 Yuzusoft 及各地发行/本地化权利方所有；`data/` 中的文本仅为技术研究与检索示例，**禁止商业使用、禁止二次分发、禁止任何形式的盈利或替代正版**。
> - **请支持正版**：使用本项目前，请先通过 Steam 等正规渠道购买并合法拥有游戏；本项目**不鼓励、不支持、不参与任何盗版行为**。请自行确认所在地区的法律法规，因使用产生的法律风险由使用者自负。
> - **无担保**：代码与数据均按 **"AS IS"** 提供，不保证正确性、完整性、可用性或安全性；作者不对因使用本项目造成的任何直接或间接损失（包括但不限于数据丢失、账号异常、法律纠纷）承担任何责任。
> - **同人研究**：`research/`、`runtime/` 等目录中的角色心理/语气/行为研究属于粉丝研究与生成验证，**不代表官方设定**，也不构成对原作角色的官方诠释；其中任何模型、提示词或生成内容均不得作为官方资料引用。
> - **侵权联系**：若权利方认为本项目任何内容侵犯其权益，请通过 GitHub Issue 联系作者，作者将在核实后尽快删除或调整相关内容。
> - **使用即同意**：下载、克隆、运行或以任何方式使用本项目，即视为已阅读并同意以上全部条款；如不同意，请立即停止使用并删除本项目所有副本。

# SenrenBanka-CN-Text-Extractor

从 **《千恋＊万花 / Senren Banka》（Yuzusoft，Steam 简体中文版）** 的 `scn.xp3` 中
**无需运行游戏、无需 GUI 工具**，纯脚本解包并提取**按角色分装的简体中文台词**。

- 依赖：仅 Python 3.8+ 标准库（不需要 numpy / 第三方库）
- 平台：Windows / Linux / macOS 通用
- 产出：`data/characters/<角色名>.json` × 98 + `narration.json`（旁白）+ `_summary.json`
- 另有**按线路→场景还原的连续剧本**：`data/transcripts/<线路>/<场景>.md` × 86（`scripts/extract_scenes.py` 生成）
- 已提取好的文本全部在本仓库 `data/`，可直接取用

## 结果概览

| 项目 | 数值 |
|---|---|
| 剧本文件（.ks.scn） | 89 个（共同线 + 芳乃/茉子/ムラサメ(丛雨)/レナ(蕾娜)/小春/芦花 全线路 + FD） |
| 对白条目 | **44,508** 条（含语音号 `voice` 字段，可对照语音） |
| 旁白/无说话人文本 | 13,077 条 |
| 主要角色台词数 | 将臣 11530 / 丛雨 3498 / 芳乃 3465 / 茉子 3409 / 蕾娜 2555 / 芦花 1543 / 小春 1230 / 廉太郎 1020 … |

文本为游戏内置官方简体翻译（脚本内同时含 日/英/简中/繁中 四轨，本工具取第 3 轨）。

## 快速开始

对任意一份千恋＊万花游戏目录（需要 `scn.xp3`）：

```bat
:: 1. 解包 + 解密 scn.xp3（输出 *.ks.scn 到 out\scn_raw）
python scripts\xp3_extract.py "E:\SteamLibrary\steamapps\common\SenrenBanka\scn.xp3" out\scn_raw

:: 2a. （可选）用 FreeMoteToolkit 的 PsbDecompile.exe 批量反编译成 JSON
PsbDecompile.exe out\scn_raw

:: 2b. 没有 FreeMote 也行：extract_text.py 会优先读 .ks.json，读不到就直接用
::     内置 PSB 解析器解析 .scn（psb_parser.py，纯 Python）
python scripts\extract_text.py
:: 输出到 characters\ 目录
```

> `extract_text.py` 默认在脚本同级的 `scn_raw/` 找输入、写 `characters/`，
> 路径写在文件开头常量里，按需修改。

输出的每个角色文件格式：

```json
{
 "character": "丛雨",
 "count": 3498,
 "lines": [
   {"file": "001・アーサー王ver1.07", "text": "「吾名丛雨，乃是这“丛雨丸”的管理者……」", "voice": "mur001_005"}
 ]
}
```

## 目录结构

```
scripts/
  xp3_extract.py        XP3 v2 解包 + SenrenCxCrypt(cxdec) 内容解密（纯 Python）
  psb_parser.py         PSB v3 解析器（FreeMote 语义的 Python 移植）
  extract_text.py       遍历对白结构 → 按角色聚合输出 JSON
  solve_region_key.py   区域密钥异常时的 adler32 代数求解器（见下文"坑 5"）
  xp3data/senren_banka.bin   Senren Banka 加密控制块（0x400 × u32）
                         来源：lifegpc/msg-tool 仓库（同款数据已公开），MIT
data/characters/*.json  提取好的简中文本（Unlicense，见 LICENSE）
```

---

# 技术细节 & 踩坑记录（重点，防止后人重复试错）

千恋＊万花 = KiriKiri Z 引擎 + XP3 v2 封包 + Yuzusoft 定制的 **cxdec（`SenrenCxCrypt`）加密**。
整个链路是：**XP3 目录解析 → 文件名还原 → 内容解密 → PSB 反编译 → 对白结构抽取**。
下面按链路顺序把每个环节的格式与坑写清楚。

## 0. XP3 v2 文件头

XP3 v2（KiriKiri Z 时代）的魔数是 **11 字节**：

```
58 50 33 0D 0A 20 0A 1A 8B 67 01     "XP3\r\n \n\x1a\x8b\x67\x01"
```

注意旧版（KiriKiri2）魔数只有 9 字节（末尾 `8B 67 01` 不同）。
- 偏移 0x0B：u64 → 目录（TOC）偏移；
- 目录处若 u32 == 0x80 表示目录偏移本身被重定向（再读 +9 处的 u64）；
- 目录头 1 字节类型：0 = 裸目录，1 = zlib 压缩目录（本作为 1）。

目录为一系列 `[u32 tag][u64 size][body]` 条目：`File`（含 `info`/`segm`/`adlr` 子节）、
以及本作特有的 **`sen:` 节**（见坑 2）。

## 1. cxdec（SenrenCxCrypt）内容解密

每条 `File` 的解密密钥就是其 **`adlr` 字段**。
**黄金校验：`adlr == adler32(解密后明文)`**（本作 `adlr` 兼作内容校验和与解密密钥，
解包器可用它 100% 验证每个文件解密正确性——强烈建议实现）。

解密规则（移植 GARbro `KiriKiriCx.cs`）：

- `base = (hash & Mask) + Offset`；文件流 `[0, base)` 用原键 `hash`，`[base, end)` 用折叠键 `(hash >> 16) ^ hash`；
- 每个区域调用 xcode 虚拟机：`ret1 = exec(hash >> 7)`，`ret2 = exec(~(hash >> 7))`；
  - `key3 = ret1 & 0xFF`（为 0 则取 1），整个区域逐字节 XOR `key3`；
  - `key1 = ret2 >> 16` 处再 XOR `(ret1 >> 8) & 0xFF`；
  - `key2 = ret2 & 0xFFFF` 处再 XOR `(ret1 >> 16) & 0xFF`；
  - **key1/key2 是"绝对流偏移"**（区域划分不影响其绝对性）。
- xcode 程序按 `seed = key & 0x7F` 用 LCG 随机生成（上限 0x80 字节码，失败降 stage 重试），
  执行时可能读取 **0x400 项控制块**（来自游戏 TPM 插件；本作控制块已提取为
  `scripts/xp3data/senren_banka.bin`，注意执行时还要**按位取反**一次）。

**本作常量（来自 msg-tool 数据库）**：`Mask=308, Offset=1846`，
`PrologOrder="AQAC"`、`OddBranchOrder="AwECBAAF"`、`EvenBranchOrder="BwQDBgIAAQU="`（base64），
文件名节 tag = `"sen:"`。

### 坑 1：stage 回退时 RNG 状态必须延续
GARbro 的 `GenerateProgram` 对同一个 program 实例从 stage 5 降到 1 重试时
**只清空 code，不清 LCG 状态（m_seed）**。如果按"每次新建实例"实现，
部分 seed 生成的程序会与真实引擎不同 → 对应文件解密错误
（症状：文件头 `PSB` 魔数正常、深处数组解析爆炸）。

### 坑 2：文件名混淆与 `sen:` 节
所有条目 `info` 里的名字是 32 位十六进制乱码（MD5）。还原方法：
- TOC 里的 `sen:` 节 body = `[u64 偏移][u32 解压大小][u32 压缩大小]`，
  按偏移从归档读 zlib 流，解压后仍是一串 `[u32 tag][u64 size][u32 hash][u16 名长][UTF-16LE 名字]` 条目；
- 建立 `MD5(名字.lower().encode('utf-16-le')) → 名字` 映射替换 `info` 名即可。
- 首条目是一个防盗版诱饵：名字超长且含 Windows 非法字符，需跳过。

### 坑 3：解密偏移语义
GARbro 对压缩段是**先 zlib 解压、再以"解压后流内相对偏移"解密**（单段文件从 0 开始）；
msg-tool 的 `Segment.offset_in_file` 也是"段内在原始文件中的累计偏移"（单段=0），
两者一致。**不要**把归档内绝对偏移掺进去。

### 坑 4：key1/key2 的配对
`key2 = ret2 & 0xFFFF ↔ (ret1 >> 16) & 0xFF`，`key1 = ret2 >> 16 ↔ (ret1 >> 8) & 0xFF`。
两两配对写反不会有任何报错，只是随机若干字节错 → 极难排查。

### 坑 5：个别文件的"区域键异常"（`200・茉子－語らいver1.00.ks.scn`）
89 个文件中 88 个用上述规则即可。**唯独 200** 折叠区真实 key3 = **0x80**，
而 `key3(fold(hash)) = 0x76`（结构、字符串区全部按 0x80 成立）。
处理办法（`scripts/solve_region_key.py`）：
1. 确定真实 key3：拿已知结构（字符串偏移数组的 `[type][count][entry_type]` 头、
   参数串文本 ` #0,-12,0,-4,...`）做已知明文，对 256 个候选常量逐一验证；
2. 用 **adler32 代数**解出缺失的 2 个特殊字节：设修正字节在位置 P、值为 v，
   对 adler32 的 `a` 分量贡献 `δ = (y^v) - y`，对 `b` 分量贡献 `δ × (n - P)`（mod 65521）；
   联立 `Σδ ≡ Δa`、`Σδ(n-P) ≡ Δb` 枚举 `P ∈ [0,65535]`、`v ∈ [1,255]`，
   命中 `adler32 == adlr` 的解；
3. 用 PSB 全树解析成功 + adler32 匹配双确认（本例 adler 有多解，靠解析唯一化）。

> 推测该文件是游戏更新批次打包差异所致；若你解其它 Yuzusoft 游戏遇到
> "只有个别文件不对"，可原样套用这套求解器。

### 坑 6：Windows 控制台 GBK
Python 脚本打印日文文件名会 `UnicodeEncodeError`，开头加
`sys.stdout.reconfigure(encoding="utf-8")`（或运行时加 `-X utf8`）。

## 2. PSB v3（.ks.scn）反编译

`.ks.scn` 是 PSB v3 容器（`PSB\0` + version=3）。可用 FreeMoteToolkit 的
`PsbDecompile.exe` 批量转 JSON（命令行支持整个目录），也可用本仓库的
`psb_parser.py`（移植 FreeMote 语义：名字 btree、字符串偏移、List=0x20 / Objects=0x21、
`[type宽度][count][entry_type][数据]` 数组布局等）。

- 坑：FreeMote 遇到 `PsbArray` count 超过 int32 会抛 "Long array is not supported yet"——
  但如果是**密钥错误导致的垃圾 count**，说明解密还有问题，别急着怪解析器；
- PSB 头部布局：`@8 HeaderLength(=0x2C)`、`@12 OffsetNames`、`@16 OffsetStrings`、
  `@20 OffsetStringsData`、`@24/28/32 Chunk`、`@36 OffsetEntries`；
- 名字区是 **byte-tree**（Charset/NamesData/NameIndexes 三个数组，见 `LoadNames` 算法）。

### 对白结构（在 PSB 树里递归搜索）

```json
[说话人JP或null, null,
 [ [null,"日文"], [英名或null,"英文"], [中名或null,"简体中文"], [繁名,"繁體中文"] ],
 [ {"name": "ムラサメ", "pan": 0, "type": 0, "voice": "mur002_001"} ] 或 null,
 序号, {场景指令...}]
```

判定条件：`len>=4 且 o[1] is None 且 o[2] 是 [k,v] 对列表`；取 `o[2][2]` = `[简中说话人, 简中文本]`，
`o[3]` 里抽 `voice`。说话人优先用简中名，缺省时回退日文名（可跨条目建 JP→CN 映射）。

## 3. 校验建议

- 每个解密文件强制 `adler32 == adlr`；
- 反编译后与
  [KitsuneX07/Dataset_Maker_for_Galgames](https://github.com/KitsuneX07/Dataset_Maker_for_Galgames)
  的日文 `scripts_json/*.json` 按 `voice` 号对齐抽查（本仓库对齐率 3293/3498，日中语义一致；
  差值是对方 Text_Cleaner 过滤规则所致）。

## 4. 已知边界

- 仅覆盖 `scn.xp3`（Steam 版主剧本）。`adult.xp3 / adult2.xp3 / patch.xp3`（R18 补丁）
  用同一套脚本即可解（`xp3_extract.py` 直接换路径运行），本仓库文本不含其内容；
- `charvoice.scn / classlist.scn / scenelist.scn` 等系统脚本也在 `data` 之外未入库；
- 若游戏更新导致 `adlr` 密钥变化，重跑一遍即可。

## 致谢

- [GARbro (morkt)](https://github.com/morkt/GARbro) —— XP3/CxEncryption/SenrenCxCrypt 参考实现（MIT）
- [lifegpc/msg-tool](https://github.com/lifegpc/msg-tool) —— Senren Banka 方案常量与控制块 `senren_banka.bin`（MIT）
- [yuzu-xp3 (crates.io)](https://docs.rs/yuzu-xp3) —— 算法交叉验证
- [UlyssesWu/FreeMote](https://github.com/UlyssesWu/FreeMote) —— PSB 反编译器
- [KitsuneX07/Dataset_Maker_for_Galgames](https://github.com/KitsuneX07/Dataset_Maker_for_Galgames) ——
  思路来源与日文校对数据
- [elix.homes 解包教程](https://elix.homes/2025/11/29/【解包】获取GalGame文本、音频方法及格式化对应/) —— GARbro + FreeMote 流程参考

## 许可

代码与提取文本均以 **The Unlicense**（公有领域）发布，见 [LICENSE](LICENSE)。
游戏文本版权归 Yuzusoft / NekoNyan / Hikari Field 等原权利方所有，
本仓库仅作技术研究与学习用途。

## data/transcripts —— 按线路/场景的连续剧本

`scripts/extract_scenes.py` 将每个场景的全部对白+旁白按脚本原始顺序还原成
Markdown 剧本（**角色**：台词，旁白为正文段落），按章节分目录：

| 目录 | 场景数 | 内容 |
|---|---|---|
| 01_共通线 | 15 | 001–015 开场～正常 End |
| 02_芳乃线 | 15 | 100–114 |
| 03_茉子线 | 11 | 200–210 |
| 04_丛雨线 | 16 | 301–316（ムラサメちゃんルート） |
| 05_蕾娜线 | 15 | 414–428（レナ） |
| 06_小春・芦花线 | 14 | 501–522（サブルート） |

范例（`data/transcripts/04_丛雨线/301・ムラサメちゃんルート０１ver1.3.md`）：

> **将臣**：「接下来」
>
> 抱在怀里的包比我想象中还要轻。
