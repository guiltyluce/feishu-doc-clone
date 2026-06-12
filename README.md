# 飞书文档蒸馏助手 / feishu-doc-clone

中文 | [English](README.en.md)

`feishu-doc-clone` 是一个用于飞书/Lark 文档高保真迁移的 Skill。它会把分享文档、知识库页面或受限文档整理成用户自己空间里的可编辑副本，尽量保留正文结构、图片、表格和代码块。

“蒸馏”在这里指把原文中真正有用的结构与内容提取出来，重新沉淀成可编辑、可归档、可继续协作的文档。

## 适合场景

- 飞书文档无复制权限，但需要保存到自己的空间。
- 知识库文档需要迁移到个人或团队知识库。
- 原生复制后图片、表格或代码块丢失。
- 需要把分享资料变成可编辑的内部沉淀文档。

## 核心能力

- 解析飞书文档、docx 和 wiki-backed doc。
- 优先尝试官方复制接口。
- 复制失败时使用 fetch JSON + Markdown 重建。
- 克隆前盘点源文档块类型，附件、画板、电子表格等不可静默丢失，逐项交代去向。
- 图片无法直接下载时，使用登录浏览器提取可见图片，缺图定点补抓。
- 显式 token 映射重传图片，画板转为静态快照，附件重新插入。
- 长文档安全分块创建，防止单次 API 调用截断。
- 对比源文档和副本：代码块、正文（含截断定位）、图片数任一缺口即判失败。

## 目录

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

## 快速检查

```bash
python3 scripts/validate_skill_package.py --zip
python3 scripts/compare_clone.py --help
```

## Skill 安装

SKILL.md 是跨 Agent 通用格式，同一份包可在多个环境使用。

本地 CLI（自动安装到 Claude Code `~/.claude/skills/` 和 Codex `~/.codex/skills/`）：

```bash
bash scripts/install.sh
```

上传类平台（claude.ai Skills、WorkBuddy 等）：上传分发包

```bash
bash scripts/package.sh   # 重建 skill/feishu-doc-clone/feishu-doc-clone.zip
```

## License

MIT
