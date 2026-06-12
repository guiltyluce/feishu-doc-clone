#!/usr/bin/env python3
"""Split a fetched Feishu doc JSON into text parts and media placeholders.

Recognizes Feishu fetch-markdown special tags regardless of attribute order:
<image/>, <file/>, <whiteboard/>, <sheet/>, <bitable/>, <iframe/>.
Every special tag is captured so nothing is silently dropped; tags the
markdown pipeline cannot carry are listed in the plan's gap summary.
"""

import argparse
import json
import re
from pathlib import Path


TAG_RE = re.compile(
    r"<(image|file|whiteboard|sheet|bitable|iframe)\b([^<>]*?)/?>"
    r"|<!--\s*Unsupported block type: (\d+)\s*-->",
    re.IGNORECASE,
)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

# How each tag kind travels through the markdown rebuild pipeline:
#   reupload     download or browser-extract the image, upload, swap token
#   snapshot     download whiteboard thumbnail, insert it as an image
#   passthrough  url-based tag can be recreated verbatim
#   append       re-upload via `docs +media-insert --type file` at doc end
#   unsupported  cannot be migrated; must be reported to the user
MIGRATION = {
    "image": "reupload",
    "whiteboard": "snapshot",
    "iframe": "passthrough",
    "file": "append",
    "sheet": "unsupported",
    "bitable": "unsupported",
}


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
    media = []
    last = 0
    for match in TAG_RE.finditer(markdown):
        if match.group(3):  # <!-- Unsupported block type: N -->
            kind = f"unsupported_block_{match.group(3)}"
            attrs = {}
            MIGRATION.setdefault(kind, "unsupported")
        else:
            kind = match.group(1).lower()
            attrs = dict(ATTR_RE.findall(match.group(2)))
        parts.append(markdown[last : match.start()])
        media.append(
            {
                "index": len(media),
                "kind": kind,
                "migration": MIGRATION[kind],
                "tag": match.group(0),
                "token": attrs.get("token", ""),
                "attrs": attrs,
            }
        )
        last = match.end()
    parts.append(markdown[last:])

    counts: dict[str, int] = {}
    for item in media:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    gaps = [
        {"kind": item["kind"], "token": item["token"], "name": item["attrs"].get("name", "")}
        for item in media
        if item["migration"] in ("append", "unsupported")
    ]

    plan = {
        "title": data.get("title") or "",
        "doc_id": data.get("doc_id") or "",
        "parts": parts,
        "media": media,
        "counts": counts,
        "gaps": gaps,
    }
    Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "title": plan["title"],
                "parts": len(parts),
                "media": len(media),
                "counts": counts,
                "upload_tokens": [m["token"] for m in media if m["migration"] in ("reupload", "snapshot")],
                "gaps": gaps,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
