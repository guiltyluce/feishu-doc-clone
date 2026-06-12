#!/usr/bin/env python3
"""Split assembled Markdown into chunks safe for create + append calls.

Long documents fail or truncate when created in one API call. Chunks are cut
only at paragraph boundaries — never inside a code fence or a table — so
appending chunk by chunk cannot corrupt blocks. A single unit larger than
--max-bytes becomes its own oversize chunk and is reported.
"""

import argparse
import json
from pathlib import Path


def split_units(markdown: str) -> list[str]:
    """Return indivisible units: fenced code blocks, table runs, paragraphs."""
    lines = markdown.split("\n")
    units: list[list[str]] = []
    current: list[str] = []
    fence = ""
    in_table = False

    def flush() -> None:
        nonlocal current
        if current:
            units.append(current)
            current = []

    for line in lines:
        stripped_line = line.lstrip()
        if fence:
            current.append(line)
            if stripped_line.startswith(fence):
                fence = ""
                flush()
            continue
        if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
            flush()
            fence = stripped_line[:3]
            current.append(line)
            continue
        is_table_line = stripped_line.startswith("|")
        if in_table and not is_table_line:
            flush()
            in_table = False
        if is_table_line and not in_table:
            flush()
            in_table = True
        if not stripped_line and not in_table:
            current.append(line)
            flush()
            continue
        current.append(line)
    flush()
    return ["\n".join(unit) for unit in units]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", required=True, help="Assembled markdown file")
    parser.add_argument("--out-dir", required=True, help="Directory for chunk_NNN.md files")
    parser.add_argument("--max-bytes", type=int, default=30000, help="Max UTF-8 bytes per chunk (default 30000)")
    args = parser.parse_args()

    markdown = Path(args.src).read_text(encoding="utf-8")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[str] = []
    buffer = ""
    oversize: list[int] = []
    for unit in split_units(markdown):
        candidate = buffer + ("\n" if buffer and not buffer.endswith("\n") else "") + unit if buffer else unit
        if buffer and len(candidate.encode("utf-8")) > args.max_bytes:
            chunks.append(buffer)
            buffer = unit
        else:
            buffer = candidate
        if len(buffer.encode("utf-8")) > args.max_bytes:
            oversize.append(len(chunks) + 1)
            chunks.append(buffer)
            buffer = ""
    if buffer.strip():
        chunks.append(buffer)

    files = []
    for index, chunk in enumerate(chunks, start=1):
        path = out_dir / f"chunk_{index:03d}.md"
        path.write_text(chunk, encoding="utf-8")
        files.append(str(path))

    print(
        json.dumps(
            {
                "chunks": len(files),
                "files": files,
                "oversize_chunks": oversize,
                "total_bytes": len(markdown.encode("utf-8")),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
