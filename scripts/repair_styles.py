#!/usr/bin/env python3
"""Repair text blocks the Feishu create API corrupted inside callouts.

Known platform bug: a line that starts with bold (**xx**) inside a callout
is created with literal asterisks, no style, and gets MERGED with the
following lines into a single block. This script matches such final-doc
text blocks back to the source blocks (by content, ignoring the literal
markers):

- exact one-block match  -> PATCH update_text_elements with source styles
- merged multi-block match -> insert the original blocks via children
  create at the same position, then batch-delete the merged block,
  restoring both styles and paragraph structure

Usage:
  python3 repair_styles.py --source-blocks /tmp/source_blocks.json \
      --doc <final_doc_id> [--dry-run]
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


MARKER_RE = re.compile(r"\*\*|__|(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)")


def block_content(block: dict) -> str:
    if "text" not in block:
        return ""
    return "".join(e.get("text_run", {}).get("content", "") for e in block["text"].get("elements", []))


def normalized(content: str) -> str:
    return re.sub(r"\s+", "", MARKER_RE.sub("", content))


def api(method: str, path: str, data=None) -> dict:
    cmd = ["lark-cli", "api", method, path, "--as", "user",
           "--params", '{"document_revision_id":-1}' if method != "GET" else '{"page_size":500,"document_revision_id":-1}']
    if data is not None:
        cmd += ["--data", json.dumps(data, ensure_ascii=False)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(cp.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"code": -1, "msg": (cp.stdout or cp.stderr)[:200]}


def find_merge_window(src_texts, target: str):
    """Find consecutive source text blocks whose concatenated text equals target."""
    for start in range(len(src_texts)):
        joined = ""
        for end in range(start, min(start + 6, len(src_texts))):
            joined += src_texts[end][0]
            if joined == target and end > start:
                return [src_texts[i][1] for i in range(start, end + 1)]
            if len(joined) >= len(target):
                break
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-blocks", required=True, help="Source doc blocks API JSON")
    parser.add_argument("--doc", required=True, help="Final document id")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be patched")
    args = parser.parse_args()

    src_raw = json.loads(Path(args.source_blocks).read_text(encoding="utf-8"))
    src_items = src_raw.get("data", src_raw).get("items", [])
    src_by_text: dict[str, list] = {}
    src_texts: list[tuple[str, dict]] = []  # 文档顺序的 (规范化文本, block)
    for b in src_items:
        if "text" not in b:
            continue
        src_texts.append((normalized(block_content(b)), b))
        elements = b["text"].get("elements", [])
        if any(e.get("text_run", {}).get("text_element_style", {}).get(s)
               for e in elements for s in ("bold", "italic", "strikethrough", "underline", "inline_code")):
            src_by_text.setdefault(normalized(block_content(b)), []).append(elements)

    raw = api("GET", f"/open-apis/docx/v1/documents/{args.doc}/blocks")
    final_items = raw["data"]["items"]
    children_of = {b["block_id"]: b.get("children", []) for b in final_items}

    patched, skipped = [], []
    for b in final_items:
        content = block_content(b)
        if "**" not in content:
            continue
        target = normalized(content)
        candidates = src_by_text.get(target, [])
        if len(candidates) == 1:
            if args.dry_run:
                patched.append({"block_id": b["block_id"], "action": "patch", "dry_run": True})
                continue
            res = api("PATCH", f"/open-apis/docx/v1/documents/{args.doc}/blocks/{b['block_id']}",
                      {"update_text_elements": {"elements": candidates[0]}})
            (patched if res.get("code") == 0 else skipped).append(
                {"block_id": b["block_id"], "action": "patch", "ok": res.get("code") == 0, "content": content[:40]})
            continue

        window = find_merge_window(src_texts, target)
        if not window:
            skipped.append({"block_id": b["block_id"], "reason": "no source match", "content": content[:50]})
            continue
        parent = b.get("parent_id", "")
        siblings = children_of.get(parent, [])
        if b["block_id"] not in siblings:
            skipped.append({"block_id": b["block_id"], "reason": "parent children unknown", "content": content[:50]})
            continue
        index = siblings.index(b["block_id"])
        if args.dry_run:
            patched.append({"block_id": b["block_id"], "action": f"split into {len(window)}", "dry_run": True})
            continue
        children = [{"block_type": 2, "text": {"style": w["text"].get("style", {}), "elements": w["text"]["elements"]}}
                    for w in window]
        res = api("POST", f"/open-apis/docx/v1/documents/{args.doc}/blocks/{parent}/children",
                  {"index": index, "children": children})
        if res.get("code") != 0:
            skipped.append({"block_id": b["block_id"], "reason": f"insert failed: {res.get('msg','')[:80]}"})
            continue
        res = api("DELETE", f"/open-apis/docx/v1/documents/{args.doc}/blocks/{parent}/children/batch_delete",
                  {"start_index": index + len(window), "end_index": index + len(window) + 1})
        patched.append({"block_id": b["block_id"], "action": f"split into {len(window)}",
                        "ok": res.get("code") == 0, "content": content[:40]})
        if res.get("code") != 0:
            skipped.append({"block_id": b["block_id"], "reason": f"delete merged failed: {res.get('msg','')[:80]}"})

    print(json.dumps({"patched": patched, "skipped": skipped}, ensure_ascii=False, indent=1))
    if skipped:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
