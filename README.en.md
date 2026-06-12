# Feishu Doc Distiller / feishu-doc-clone

[中文](README.md) | English

`feishu-doc-clone` is a Skill for high-fidelity Feishu/Lark document migration. It turns shared documents, wiki pages, or restricted documents into editable copies in the user's own workspace while preserving text structure, images, tables, and code blocks as much as possible.

In Chinese, "distillation" here means extracting useful structure and content from the source and rebuilding it as an editable, archivable, collaborative document.

## Use Cases

- A Feishu document cannot be copied directly, but needs to be saved into the user's own workspace.
- A wiki document needs to be migrated into a personal or team knowledge base.
- Native copy loses images, tables, or code blocks.
- Shared materials need to become editable internal knowledge assets.

## Core Capabilities

- Resolve Feishu docs, docx documents, and wiki-backed documents.
- Try official copy APIs first.
- Rebuild with fetched JSON and Markdown when copy is blocked.
- Inventory source block types before rebuilding; attachments, whiteboards, and sheets are never dropped silently.
- Extract browser-visible images when direct media download is blocked, with targeted retries for missing ones.
- Re-upload images via an explicit token map; whiteboards become static snapshots, attachments are re-inserted.
- Split long documents into safe chunks to avoid single-call truncation.
- Compare source and target documents: any gap in code blocks, body text (with truncation locating), or image count fails the check.

## Repository Layout

```text
.
├── README.md
├── LICENSE
├── references/
│   └── browser-image-extraction.md
├── scripts/
│   ├── assemble_markdown.py
│   ├── compare_clone.py
│   ├── extract_plan.py
│   ├── inventory_blocks.py
│   ├── split_markdown.py
│   ├── install.sh
│   ├── package.sh
│   └── validate_skill_package.py
└── skill/
    └── feishu-doc-clone/
        ├── SKILL.md
        └── feishu-doc-clone.zip
```

## Quick Check

```bash
python3 scripts/validate_skill_package.py --zip
python3 scripts/compare_clone.py --help
```

## Skill Installation

SKILL.md is a cross-agent standard; the same package works in multiple environments.

Local CLIs (installs into Claude Code `~/.claude/skills/` and Codex `~/.codex/skills/`):

```bash
bash scripts/install.sh
```

Upload-style platforms (claude.ai Skills, WorkBuddy, etc.): upload the rebuilt package

```bash
bash scripts/package.sh   # rebuilds skill/feishu-doc-clone/feishu-doc-clone.zip
```

## License

MIT
