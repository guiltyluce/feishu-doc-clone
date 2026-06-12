#!/usr/bin/env python3
"""Assemble final Feishu Markdown from a plan and an explicit token map.

The token map is JSON mapping source token -> newly uploaded token, either
{"SRC": "NEW", ...} or a list of {"source_token": ..., "file_token": ...}
objects. Position-based matching is intentionally not supported: a retry or
extra upload must never silently shift images onto the wrong slots.
"""

import argparse
import json
import re
from pathlib import Path


# Feishu's fetch emits compact markdown (single \n between blocks), but its
# create API merges \n-separated lines into one block — paragraphs collapse
# and structure drifts. Top-level blocks must be re-separated with blank
# lines. Inside containers (callout/grid/column) single \n round-trips
# correctly and must be kept.
# Feishu's fetch writes callout emoji as a name ("bulb"), but create only
# accepts the emoji character — a name silently disables ALL inline markdown
# parsing inside that callout (bold becomes literal **). Translate known
# names; drop the attribute for unknown ones so formatting survives.
EMOJI_NAMES = {
    "bulb": "💡", "white_check_mark": "✅", "pushpin": "📌", "warning": "⚠️",
    "x": "❌", "exclamation": "❗", "question": "❓", "fire": "🔥",
    "star": "⭐", "memo": "📝", "bell": "🔔", "rocket": "🚀", "eyes": "👀",
    "dart": "🎯", "bookmark": "🔖", "link": "🔗", "lock": "🔒", "key": "🔑",
    "gear": "⚙️", "zap": "⚡", "tada": "🎉", "sparkles": "✨", "mag": "🔍",
    "books": "📚", "clipboard": "📋", "calendar": "📅", "bug": "🐛",
    "package": "📦", "thumbsup": "👍", "point_right": "👉", "heart": "❤️",
    "information_source": "ℹ️", "speech_balloon": "💬", "no_entry": "⛔",
    "stop_sign": "🛑", "triangular_flag_on_post": "🚩",
}
CALLOUT_EMOJI_RE = re.compile(r'(<callout\b[^<>]*?)\s*emoji="([A-Za-z0-9_+\-]+)"', re.IGNORECASE)


def fix_callout_emoji(markdown: str) -> str:
    def repl(match: re.Match) -> str:
        char = EMOJI_NAMES.get(match.group(2).lower())
        if char:
            return f'{match.group(1)} emoji="{char}"'
        return match.group(1)

    return CALLOUT_EMOJI_RE.sub(repl, markdown)


CONTAINER_OPEN_RE = re.compile(r"<(callout|grid|column)\b[^<>]*(?<!/)>", re.IGNORECASE)
CONTAINER_CLOSE_RE = re.compile(r"</(callout|grid|column)>", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|>\s?)")
TABLE_ROW_RE = re.compile(r"^\s*\|")


def normalize_block_breaks(markdown: str) -> str:
    lines = markdown.split("\n")
    out: list[str] = []
    fence = False
    depth = 0
    for index, line in enumerate(lines):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
        if not fence:
            depth += len(CONTAINER_OPEN_RE.findall(line)) - len(CONTAINER_CLOSE_RE.findall(line))
            depth = max(depth, 0)
        out.append(line)
        if fence or depth > 0 or index + 1 >= len(lines):
            continue
        nxt = lines[index + 1]
        if not line.strip() or not nxt.strip():
            continue
        if TABLE_ROW_RE.match(line) and TABLE_ROW_RE.match(nxt):
            continue
        if LIST_ITEM_RE.match(line) and LIST_ITEM_RE.match(nxt):
            continue
        out.append("")
    return "\n".join(out)


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

    Path(args.out).write_text(
        fix_callout_emoji(normalize_block_breaks("".join(output))), encoding="utf-8"
    )
    print(
        json.dumps(
            {"images": emitted_images, "gaps": gaps, "out": args.out},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
