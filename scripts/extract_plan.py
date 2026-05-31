#!/usr/bin/env python3
"""Split a fetched Feishu doc JSON into text parts and image metadata."""

import argparse
import json
import re
from pathlib import Path


IMAGE_RE = re.compile(
    r'<image token="([^"]*)" width="([^"]*)" height="([^"]*)" align="([^"]*)"\s*/>'
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-json", required=True, help="Output from lark-cli docs +fetch --format json")
    parser.add_argument("--out", required=True, help="Plan JSON to write")
    args = parser.parse_args()

    raw = json.loads(Path(args.fetch_json).read_text(encoding="utf-8"))
    data = raw.get("data", raw)
    markdown = data.get("markdown")
    if not isinstance(markdown, str):
        raise SystemExit("fetch JSON does not contain data.markdown")

    parts = []
    images = []
    last = 0
    for match in IMAGE_RE.finditer(markdown):
        parts.append(markdown[last : match.start()])
        images.append(
            {
                "tag": match.group(0),
                "token": match.group(1),
                "width": match.group(2),
                "height": match.group(3),
                "align": match.group(4),
            }
        )
        last = match.end()
    parts.append(markdown[last:])

    plan = {
        "title": data.get("title") or "",
        "doc_id": data.get("doc_id") or "",
        "parts": parts,
        "images": images,
    }
    Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"title": plan["title"], "parts": len(parts), "images": len(images)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
