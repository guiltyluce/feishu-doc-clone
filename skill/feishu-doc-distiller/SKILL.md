---
name: feishu-doc-distiller
description: 飞书文档蒸馏助手：将飞书或 Lark 云文档、知识库文档高保真复制到用户自己的文档空间，保留正文结构、代码块和图片；适用于无复制权限、跨空间迁移、文档沉淀和资料再整理场景。
---

# 飞书文档蒸馏助手

用于把一个飞书/Lark 云文档或知识库文档“蒸馏”为用户自己空间里的可编辑副本。优先尝试官方复制能力；复制受限或图片丢失时，转为 Markdown 重建、浏览器图片提取和媒体重传流程。

# 触发场景

用户出现以下意图时使用：

- 复制、克隆、备份飞书文档或知识库页面。
- 将别人分享的文档创建到自己的飞书文档或知识库。
- 原文无复制权限，或复制后图片、表格、代码块丢失。
- 需要保留正文结构、图片和代码块，再做二次整理。

典型表达：

- `把这个飞书文档复制到我的知识库`
- `原封不动创建一个副本`
- `这个文档不能复制，帮我重建`
- `保留图片和代码块`

# 工作流程

1. 解析来源：
   - `/wiki/<token>`：先查询知识库节点，确认对象类型是 `docx` 或 `doc`。
   - 普通文档 URL：提取文档 token。
   - 表格、多维表、文件、幻灯片等类型应切换到对应 Skill。
2. 确认目标：
   - 用户给出文件夹或知识库时，写入指定位置。
   - 用户未指定目标时，默认创建到用户个人文档空间。
3. 优先使用原生复制：
   - Drive file copy。
   - Wiki node copy。
   - 如果返回 forbidden、权限错误、空结果或目标中没有新节点，进入重建流程。
4. 重建文档：
   - 用 `lark-cli docs +fetch --as user --format json` 获取源文档结构。
   - 用 `scripts/extract_plan.py` 拆出标题、正文、图片和代码块计划。
   - 当飞书媒体下载失败时，按 `references/browser-image-extraction.md` 使用已登录浏览器提取可见图片。
   - 将图片上传到临时文档，收集新 token。
   - 用 `scripts/assemble_markdown.py` 生成最终 Markdown。
   - 一次性创建最终文档，避免多次 append 破坏代码块。
5. 验证结果：
   - 重新 fetch 目标文档。
   - 检查标题、正文长度、图片数量、空图片 token、代码块内容。
   - 对齐源文档和目标文档的文本差异，向用户说明无法完全保真的地方。

# 关键命令

拆分源文档：

```bash
python3 scripts/extract_plan.py \
  --fetch-json /tmp/source.json \
  --out /tmp/clone_plan.json
```

重组最终 Markdown：

```bash
python3 scripts/assemble_markdown.py \
  --plan /tmp/clone_plan.json \
  --uploaded-log /tmp/staging_steps.log \
  --out /tmp/final_clone.md
```

比较源文档与副本：

```bash
python3 scripts/compare_clone.py \
  --source /tmp/source.json \
  --target /tmp/final.json
```

# 注意事项

- 默认使用用户身份 `--as user`。
- 不打印 app secret、tenant token、图片下载签名或临时鉴权 URL。
- 不把源文档图片、下载文件、fetch JSON 或临时日志提交到 git。
- 图片无法直接下载时，优先使用浏览器可见内容提取；仍失败时说明缺口。
- 代码块内容必须保持精确，普通 Markdown 的空行和样式差异可以说明为平台转换差异。
