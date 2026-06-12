#!/usr/bin/env python3
"""Assemble final Feishu Markdown from a plan and an explicit token map.

The token map is JSON mapping source token -> newly uploaded token, either
{"SRC": "NEW", ...} or a list of {"source_token": ..., "file_token": ...}
objects. Position-based matching is intentionally not supported: a retry or
extra upload must never silently shift images onto the wrong slots.
"""

import argparse
import json
from pathlib import Path


def load_token_map(path: str) -> dict[str, str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items() if isinstance(v, str) and v}
    if isinstance(raw, list):
        mapping = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            src = item.get("source_token") or item.get("token") or ""
            new = item.get("file_token") or item.get("uploaded") or ""
            if src and new:
                mapping[src] = new
        return mapping
    raise SystemExit("--token-map must be a JSON object or list")


def image_tag(token: str, attrs: dict[str, str]) -> str:
    pieces = [f'token="{token}"']
    for key in ("width", "height", "align"):
        if attrs.get(key):
            pieces.append(f'{key}="{attrs[key]}"')
    return f"<image {' '.join(pieces)}/>"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Plan JSON from extract_plan.py")
    parser.add_argument("--token-map", required=True, help="JSON mapping source token -> uploaded token")
    parser.add_argument("--out", required=True, help="Markdown file to write")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    parts = plan["parts"]
    media = plan["media"]
    token_map = load_token_map(args.token_map)

    if len(parts) != len(media) + 1:
        raise SystemExit(f"bad plan: {len(parts)} parts for {len(media)} media items")

    missing = [
        item["token"]
        for item in media
        if item["migration"] == "reupload" and item["token"] not in token_map
    ]
    if missing:
        raise SystemExit(
            "token map is missing uploads for image tokens: " + ", ".join(missing)
        )

    output = [parts[0]]
    emitted_images = 0
    gaps = []
    for item, next_part in zip(media, parts[1:]):
        migration = item["migration"]
        if migration == "reupload":
            output.append(image_tag(token_map[item["token"]], item["attrs"]))
            emitted_images += 1
        elif migration == "snapshot":
            if item["token"] in token_map:
                output.append(image_tag(token_map[item["token"]], item["attrs"]))
                emitted_images += 1
            else:
                gaps.append({"kind": item["kind"], "token": item["token"], "reason": "no snapshot uploaded"})
        elif migration == "passthrough":
            output.append(item["tag"])
        else:  # append / unsupported: handled outside the inline markdown
            gaps.append(
                {
                    "kind": item["kind"],
                    "token": item["token"],
                    "name": item["attrs"].get("name", ""),
                    "reason": "re-insert after doc creation" if migration == "append" else "not migratable",
                }
            )
        output.append(next_part)

    Path(args.out).write_text("".join(output), encoding="utf-8")
    print(
        json.dumps(
            {"images": emitted_images, "gaps": gaps, "out": args.out},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
