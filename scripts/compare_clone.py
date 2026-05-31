#!/usr/bin/env python3
"""Compare source and final Feishu fetch JSON for clone-sensitive drift."""

import argparse
import json
import re
from pathlib import Path
from typing import Any


IMAGE_RE = re.compile(r'<image token="[^"]*" width="[^"]*" height="[^"]*" align="[^"]*"\s*/>')
CODE_RE = re.compile(r"```([^\n]*)\n([\s\S]*?)```")


def load_markdown(path: str) -> str:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    data: Any = raw.get("data", raw)
    markdown = data.get("markdown")
    if not isinstance(markdown, str):
        raise SystemExit(f"{path}: missing data.markdown")
    return markdown


def code_blocks(markdown: str) -> list[dict[str, str]]:
    return [{"lang": m.group(1), "body": m.group(2)} for m in CODE_RE.finditer(markdown)]


def normalized(markdown: str) -> str:
    return IMAGE_RE.sub("<IMAGE>", markdown).replace("\r\n", "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Source docs +fetch JSON")
    parser.add_argument("--final", required=True, help="Final docs +fetch JSON")
    args = parser.parse_args()

    source = load_markdown(args.source)
    final = load_markdown(args.final)
    source_blocks = code_blocks(source)
    final_blocks = code_blocks(final)

    mismatches = []
    for index, (src, dst) in enumerate(zip(source_blocks, final_blocks), start=1):
        if src != dst:
            mismatches.append(
                {
                    "index": index,
                    "source_lang": src["lang"],
                    "final_lang": dst["lang"],
                    "source_tail": src["body"][-120:],
                    "final_tail": dst["body"][-120:],
                    "source_lines": src["body"].split("\n"),
                    "final_lines": dst["body"].split("\n"),
                }
            )

    result = {
        "source_images": len(IMAGE_RE.findall(source)),
        "final_images": len(IMAGE_RE.findall(final)),
        "source_code_blocks": len(source_blocks),
        "final_code_blocks": len(final_blocks),
        "code_blocks_equal": len(source_blocks) == len(final_blocks) and not mismatches,
        "normalized_text_equal": normalized(source) == normalized(final),
        "mismatches": mismatches[:10],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["code_blocks_equal"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
