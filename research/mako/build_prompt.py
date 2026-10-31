"""把 24_integration_prompt.md 的"系统提示词"正文与三份冻结模型拼成一个可直接使用的系统提示词。

用法（在仓库根目录运行）:
  python research/mako/build_prompt.py [--user-name 将臣] [--out research/mako/24_system_prompt_assembled.txt]
只读冻结文件，不修改它们。
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
PARTS = {
    "{{MODEL_PSYCHOLOGY}}": "22_psychological_model_v2.md",
    "{{MODEL_BEHAVIOR}}": "16_role_behavior_framework.md",
    "{{MODEL_VOICE}}": "23_voice_model.md",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-name", default="将臣")
    ap.add_argument("--out", default=str(HERE / "24_system_prompt_assembled.txt"))
    a = ap.parse_args()
    src = (HERE / "24_integration_prompt.md").read_text(encoding="utf-8")
    marker = "## 系统提示词"
    if marker not in src:
        sys.exit("找不到“## 系统提示词”一节")
    body = src.split(marker, 1)[1].lstrip("\n")
    for ph, name in PARTS.items():
        if ph not in body:
            sys.exit(f"缺少占位符 {ph}")
        # 资料内部的一级、二级标题降两级，避免与提示词结构混淆
        text = (HERE / name).read_text(encoding="utf-8")
        text = "\n".join(("##" + l) if l.startswith("#") else l for l in text.splitlines())
        body = body.replace(ph, text)
    body = body.replace("{{USER_NAME}}", a.user_name)
    Path(a.out).write_text(body, encoding="utf-8")
    print(f"wrote {a.out}: {len(body)} chars")


if __name__ == "__main__":
    main()
