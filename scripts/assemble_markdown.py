#!/usr/bin/env python3
"""Assemble final Feishu Markdown using original image layout and new image tokens."""

import argparse
import json
import re
from pathlib import Path


FILE_TOKEN_RE = re.compile(r'"file_token"\s*:\s*"([^"]+)"')


def load_uploaded(args: argparse.Namespace) -> list[str]:
    if args.uploaded_log:
        text = Path(args.uploaded_log).read_text(encoding="utf-8")
        return FILE_TOKEN_RE.findall(text)

    if args.uploaded_json:
        raw = json.loads(Path(args.uploaded_json).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            values = []
            for item in raw:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    values.append(item.get("uploaded") or item.get("file_token") or "")
            return [value for value in values if value]

    raise SystemExit("provide --uploaded-log or --uploaded-json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Plan JSON from extract_plan.py")
    parser.add_argument("--uploaded-log", help="Log containing docs +media-insert JSON responses")
    parser.add_argument("--uploaded-json", help="JSON list of uploaded tokens or objects")
    parser.add_argument("--out", required=True, help="Markdown file to write")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    parts = plan["parts"]
    images = plan["images"]
    uploaded = load_uploaded(args)

    if len(parts) != len(images) + 1:
        raise SystemExit(f"bad plan: {len(parts)} parts for {len(images)} images")
    if len(uploaded) != len(images):
        raise SystemExit(f"expected {len(images)} uploaded tokens, found {len(uploaded)}")

    output = [parts[0]]
    for image, new_token, next_part in zip(images, uploaded, parts[1:]):
        output.append(
            f'<image token="{new_token}" width="{image["width"]}" '
            f'height="{image["height"]}" align="{image["align"]}"/>'
        )
        output.append(next_part)

    Path(args.out).write_text("".join(output), encoding="utf-8")
    print(json.dumps({"images": len(images), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
