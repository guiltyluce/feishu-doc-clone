#!/usr/bin/env python3
"""Count docx block types from `lark-cli api GET /open-apis/docx/v1/documents/:id/blocks`.

Run against the source doc before cloning to know what must be carried over,
and against the final doc afterwards to prove nothing was silently dropped.
Accepts multiple JSON files so paginated responses can be passed together.
"""

import argparse
import json
from pathlib import Path


BLOCK_TYPE_NAMES = {
    1: "page",
    2: "text",
    3: "heading1", 4: "heading2", 5: "heading3", 6: "heading4", 7: "heading5",
    8: "heading6", 9: "heading7", 10: "heading8", 11: "heading9",
    12: "bullet",
    13: "ordered",
    14: "code",
    15: "quote",
    17: "todo",
    18: "bitable",
    19: "callout",
    20: "chat_card",
    21: "diagram",
    22: "divider",
    23: "file",
    24: "grid",
    25: "grid_column",
    26: "iframe",
    27: "image",
    28: "widget",
    29: "mindnote",
    30: "sheet",
    31: "table",
    32: "table_cell",
    33: "view",
    34: "quote_container",
    35: "task",
    36: "okr",
    40: "add_ons",
    41: "jira_issue",
    42: "wiki_catalog",
    43: "board",
    44: "agenda",
}

# Kinds the markdown rebuild pipeline cannot fully carry; surface them.
ATTENTION = {"file", "sheet", "bitable", "board", "iframe", "mindnote", "diagram", "widget"}


def iter_items(raw) -> list[dict]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    data = raw.get("data", raw)
    return [item for item in data.get("items", []) if isinstance(item, dict)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocks_json", nargs="+", help="Blocks API response JSON file(s)")
    args = parser.parse_args()

    counts: dict[str, int] = {}
    total = 0
    for path in args.blocks_json:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in iter_items(raw):
            block_type = item.get("block_type")
            name = BLOCK_TYPE_NAMES.get(block_type, f"unknown_{block_type}")
            counts[name] = counts.get(name, 0) + 1
            total += 1

    attention = {name: count for name, count in counts.items() if name in ATTENTION or name.startswith("unknown_")}
    print(
        json.dumps(
            {"total_blocks": total, "counts": dict(sorted(counts.items())), "attention": attention},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
