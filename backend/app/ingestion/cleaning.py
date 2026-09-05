import re

_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_BREAK = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _MULTI_SPACE.sub(" ", raw).strip()
        if line:
            lines.append(line)
    return _MULTI_BREAK.sub("\n\n", "\n".join(lines)).strip()
