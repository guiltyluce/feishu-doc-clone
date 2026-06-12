#!/usr/bin/env python3
"""Compare source and final Feishu fetch JSON for clone-sensitive drift.

Exits non-zero when the clone is incomplete: code blocks differ, text differs
(including truncation), or the final doc carries fewer images than expected.
Counts for every special block kind are reported so no loss stays silent.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any


TAG_RE = re.compile(r"<(image|file|whiteboard|sheet|bitable|iframe)\b[^<>]*?/?>", re.IGNORECASE)
UNSUPPORTED_RE = re.compile(r"<!--\s*Unsupported block type: \d+\s*-->", re.IGNORECASE)
CODE_RE = re.compile(r"```([^\n]*)\n([\s\S]*?)```")
# Styled containers whose attributes Feishu normalizes on create (e.g. callout
# loses border-color). Attribute drift is reported, not fatal; inner text stays strict.
STYLE_TAG_RE = re.compile(r"<(callout)\b[^<>]*>", re.IGNORECASE)


def load_markdown(path: str) -> str:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    data: Any = raw.get("data", raw)
    markdown = data.get("markdown")
    if not isinstance(markdown, str):
        raise SystemExit(f"{path}: missing data.markdown")
    return markdown


def code_blocks(markdown: str) -> list[dict[str, str]]:
    return [{"lang": m.group(1), "body": m.group(2)} for m in CODE_RE.finditer(markdown)]


def kind_counts(markdown: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in TAG_RE.finditer(markdown):
        kind = match.group(1).lower()
        counts[kind] = counts.get(kind, 0) + 1
    unsupported = len(UNSUPPORTED_RE.findall(markdown))
    if unsupported:
        counts["unsupported_block"] = unsupported
    return counts


def stripped(markdown: str) -> str:
    """Normalize for content comparison: drop media tags, style attrs, and
    collapse whitespace (Feishu's create/fetch round-trip rewrites blank
    lines). Any missing character still fails; truncation is still located."""
    text = TAG_RE.sub("", markdown).replace("\r\n", "\n")
    text = UNSUPPORTED_RE.sub("", text)
    text = STYLE_TAG_RE.sub(lambda m: f"<{m.group(1).lower()}>", text)
    return re.sub(r"\s+", "", text)


def style_diffs(source: str, final: str) -> list[dict[str, str]]:
    src_tags = [m.group(0) for m in STYLE_TAG_RE.finditer(source)]
    dst_tags = [m.group(0) for m in STYLE_TAG_RE.finditer(final)]
    diffs = []
    for index, (src, dst) in enumerate(zip(src_tags, dst_tags), start=1):
        if src != dst:
            diffs.append({"index": index, "source": src, "final": dst})
    return diffs


def first_divergence(a: str, b: str) -> dict[str, Any]:
    limit = min(len(a), len(b))
    pos = next((i for i in range(limit) if a[i] != b[i]), limit)
    if pos == limit and len(a) == len(b):
        return {}
    info: dict[str, Any] = {
        "position": pos,
        "source_context": a[max(0, pos - 60) : pos + 60],
        "final_context": b[max(0, pos - 60) : pos + 60],
    }
    if pos == limit and len(b) < len(a):
        info["truncated"] = f"final text ends at char {len(b)} of {len(a)} (likely truncated)"
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Source docs +fetch JSON")
    parser.add_argument("--final", required=True, help="Final docs +fetch JSON")
    parser.add_argument(
        "--expect-images",
        type=int,
        default=None,
        help="Expected image count in final doc (default: source image count; "
        "raise it when whiteboards were snapshotted into images)",
    )
    parser.add_argument(
        "--strict-media",
        action="store_true",
        help="Also fail when any non-image kind (file/whiteboard/sheet/bitable/iframe) lost count",
    )
    parser.add_argument(
        "--fills",
        help="Fills JSON given to assemble_markdown.py; their text is deliberately "
        "added to the clone and is excluded from the text comparison",
    )
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
                }
            )

    source_counts = kind_counts(source)
    final_counts = kind_counts(final)
    source_text = stripped(source)
    final_text = stripped(final)
    if args.fills:
        for item in json.loads(Path(args.fills).read_text(encoding="utf-8")):
            fill_text = stripped(item["markdown"])
            # fetch 可能把 [text](url) 渲染成纯链接文本，两种形态都剔除
            link_label = stripped(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", item["markdown"]))
            for candidate in (fill_text, link_label):
                if candidate and candidate in final_text:
                    final_text = final_text.replace(candidate, "", 1)
                    break

    expected_images = args.expect_images if args.expect_images is not None else source_counts.get("image", 0)
    images_ok = final_counts.get("image", 0) >= expected_images
    code_ok = len(source_blocks) == len(final_blocks) and not mismatches
    text_ok = source_text == final_text

    media_gaps = [
        {"kind": kind, "source": count, "final": final_counts.get(kind, 0)}
        for kind, count in sorted(source_counts.items())
        if kind != "image" and final_counts.get(kind, 0) < count
    ]
    media_ok = not media_gaps if args.strict_media else True

    result = {
        "ok": code_ok and text_ok and images_ok and media_ok,
        "code_blocks_equal": code_ok,
        "text_equal": text_ok,
        "images_ok": images_ok,
        "expected_images": expected_images,
        "source_counts": source_counts,
        "final_counts": final_counts,
        "source_code_blocks": len(source_blocks),
        "final_code_blocks": len(final_blocks),
        "media_gaps": media_gaps,
        "style_diffs": style_diffs(source, final)[:10],
        "code_mismatches": mismatches[:10],
    }
    if not text_ok:
        result["divergence"] = first_divergence(source_text, final_text)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
