# 飞书文档蒸馏助手 / feishu-doc-clone

`feishu-doc-clone` 是一个用于飞书/Lark 文档高保真迁移的 Skill。它会把分享文档、知识库页面或受限文档整理成用户自己空间里的可编辑副本，尽量保留正文结构、图片、表格和代码块。

`feishu-doc-clone` is a Skill for high-fidelity Feishu/Lark document migration. It turns shared documents, wiki pages, or restricted documents into editable copies in the user's own workspace while preserving text structure, images, tables, and code blocks as much as possible.

“蒸馏”在这里指把原文中真正有用的结构与内容提取出来，重新沉淀成可编辑、可归档、可继续协作的文档。

In Chinese, "distillation" here means extracting useful structure and content from the source and rebuilding it as an editable, archivable, collaborative document.

## 适合场景 / Use Cases

- 飞书文档无复制权限，但需要保存到自己的空间。
- A Feishu document cannot be copied directly, but needs to be saved into the user's own workspace.
- 知识库文档需要迁移到个人或团队知识库。
- A wiki document needs to be migrated into a personal or team knowledge base.
- 原生复制后图片、表格或代码块丢失。
- Native copy loses images, tables, or code blocks.
- 需要把分享资料变成可编辑的内部沉淀文档。
- Shared materials need to become editable internal knowledge assets.

## 核心能力 / Core Capabilities

- 解析飞书文档、docx 和 wiki-backed doc。
- Resolve Feishu docs, docx documents, and wiki-backed documents.
- 优先尝试官方复制接口。
- Try official copy APIs first.
- 复制失败时使用 fetch JSON + Markdown 重建。
- Rebuild with fetched JSON and Markdown when copy is blocked.
- 图片无法直接下载时，使用登录浏览器提取可见图片。
- Extract browser-visible images when direct media download is blocked.
- 重新上传图片并替换为目标文档中的新 token。
- Re-upload images and replace them with target-document media tokens.
- 对比源文档和副本，输出保真度检查结果。
- Compare source and target documents and report fidelity checks.

## 目录 / Repository Layout

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

## 快速检查 / Quick Check

```bash
python3 scripts/validate_skill_package.py --zip
python3 -m py_compile scripts/assemble_markdown.py scripts/compare_clone.py scripts/extract_plan.py
python3 scripts/compare_clone.py --help
```

## Skill 安装 / Skill Installation

Skill 分发包位置：

The distributable Skill package is located at:

```text
skill/feishu-doc-clone/feishu-doc-clone.zip
```

安装到本地 Skill 目录：

Install it into the local Skill directory:

```bash
mkdir -p ~/.codex/skills
unzip -o skill/feishu-doc-clone/feishu-doc-clone.zip -d ~/.codex/skills/
```

## License

MIT
