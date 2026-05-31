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
- Extract browser-visible images when direct media download is blocked.
- Re-upload images and replace them with target-document media tokens.
- Compare source and target documents and report fidelity checks.

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
│   └── validate_skill_package.py
└── skill/
    └── feishu-doc-clone/
        ├── SKILL.md
        └── feishu-doc-clone.zip
```

## Quick Check

```bash
python3 scripts/validate_skill_package.py --zip
python3 -m py_compile scripts/assemble_markdown.py scripts/compare_clone.py scripts/extract_plan.py
python3 scripts/compare_clone.py --help
```

## Skill Installation

The distributable Skill package is located at:

```text
skill/feishu-doc-clone/feishu-doc-clone.zip
```

Install it into the local Skill directory:

```bash
mkdir -p ~/.codex/skills
unzip -o skill/feishu-doc-clone/feishu-doc-clone.zip -d ~/.codex/skills/
```

## License

MIT
