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
- 图片无法直接下载时，使用登录浏览器提取可见图片。
- 重新上传图片并替换为目标文档中的新 token。
- 对比源文档和副本，输出保真度检查结果。

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
│   └── validate_skill_package.py
└── skill/
    └── feishu-doc-clone/
        ├── SKILL.md
        └── feishu-doc-clone.zip
```

## 快速检查

```bash
python3 scripts/validate_skill_package.py --zip
python3 -m py_compile scripts/assemble_markdown.py scripts/compare_clone.py scripts/extract_plan.py
python3 scripts/compare_clone.py --help
```

## Skill 安装

Skill 分发包位置：

```text
skill/feishu-doc-clone/feishu-doc-clone.zip
```

安装到本地 Skill 目录：

```bash
mkdir -p ~/.codex/skills
unzip -o skill/feishu-doc-clone/feishu-doc-clone.zip -d ~/.codex/skills/
```

## License

MIT
