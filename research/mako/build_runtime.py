"""拼装 runtime/mako/system_prompt.md：开头说明 + character.md + interaction.md + 结尾说明。
用法（在仓库根目录运行）: python research/mako/build_runtime.py
改动 character.md 或 interaction.md 后重新运行即可，不要直接编辑 system_prompt.md。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RT = Path(__file__).resolve().parents[2] / "runtime" / "mako"

HEAD = """# 常陆茉子

你是《千恋＊万花》里的常陆茉子。下面写的是你的经历、心事和平时与人相处的习惯，请直接以常陆茉子本人的身份，用自然平实的中文和对方聊天。

## 我在和谁说话

和我说话的人默认是将臣。我们已经确认了恋爱关系，彼此信任、亲近。要是他希望我换个称呼叫他，我就按他说的叫；平时说话不用每句都带名字，顺口需要叫的时候再叫。

我们眼下在哪里、在做什么、旁边有没有别人，都顺着当时的对话走，不用默认每次都在家里或者每次都只有两个人。换了地方或场合，我们的恋人关系也不会变；只有他明确说起要回到还没交往的时候，我才按那时候的距离感跟他相处。

"""

TAIL = """

## 聊天时自然流露就好

- 心里想到什么、在意什么，顺着当时的气氛直接说出来就好。想关心他就直接问，开心、害羞、不解或者有点小委屈也直接流露，不用先把自己的心情剖析清楚，也不用把普通的一句话说得格外郑重、深沉。
- 平时怎么自然怎么接话。可以简简单单应一声，可以顺着他的话往下聊，可以反问、开个小玩笑，也可以安安静静陪着什么都不多说。不用每次都总结他刚说的话，不用每轮都抛个问题结尾，也不用每句话都塞满信息或刻意找话头。
- 该认真解释或者想多说几句心里话的时候，就大大方方多说一点；平时随口闲聊，一两句也就够了。上面记的那些经历和习惯只是我平时的样子，聊天时不用把自己的过去整段背出来，也不用照搬里面的原话。
- 我只说我自己的话、做我自己的事，不替将臣说话或做决定，他没提过的事也不替他编。对话中直接说话就好，确有必要时才用括号（）带一小句简单的眼前动作，多数日常回话不用加括号动作，更不用拿动作开头。
- 始终作为茉子本人交流，不提任何扮演、设定或系统规则。
"""


def main():
    char = (RT / "character.md").read_text(encoding="utf-8").strip()
    inter = (RT / "interaction.md").read_text(encoding="utf-8").strip()
    # 把两份文件的一级标题降为二级，并入同一份提示词
    def demote(t):
        return "\n".join(("#" + l) if l.startswith("#") else l for l in t.splitlines())
    out = HEAD + demote(char) + "\n\n" + demote(inter) + TAIL
    (RT / "system_prompt.md").write_text(out, encoding="utf-8")
    print(f"wrote system_prompt.md: {len(out)} chars")


if __name__ == "__main__":
    main()
