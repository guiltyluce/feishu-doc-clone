---
name: feishu-doc-clone
description: 飞书文档蒸馏助手：将飞书或 Lark 云文档、知识库文档高保真复制到用户自己的文档空间，保留正文结构、代码块和图片；适用于无复制权限、跨空间迁移、文档沉淀和资料再整理场景。
---

# 飞书文档蒸馏助手

GitHub: [guiltyluce/feishu-doc-clone](https://github.com/guiltyluce/feishu-doc-clone)

用于把一个飞书/Lark 云文档或知识库文档"蒸馏"为用户自己空间里的可编辑副本。优先尝试官方复制能力；复制受限或图片丢失时，转为 Markdown 重建、浏览器图片提取和媒体重传流程。

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
4. 盘点源文档（重建前必做）：
   - 用 `lark-cli api GET /open-apis/docx/v1/documents/<doc_id>/blocks --as user --params '{"page_size":500,"document_revision_id":-1}'` 拉取块列表（有分页时全部拉完）。
   - 用 `scripts/inventory_blocks.py` 统计块类型。`attention` 清单（附件、画板、电子表格、多维表等）就是后续必须向用户交代去向的块，**一个都不能静默丢弃**。
5. 重建文档：
   - 用 `lark-cli docs +fetch --as user --format json` 获取源文档结构。
   - 用 `scripts/extract_plan.py` 拆出正文、图片和各类媒体块。输出中的 `upload_tokens` 是需要重传的图片/画板 token，`gaps` 是 markdown 通道带不过去的块。
   - 当飞书媒体下载失败时，按 `references/browser-image-extraction.md` 使用已登录浏览器提取可见图片；缺哪张就定位补抓哪张，直到与 `upload_tokens` 数量对齐或确认抓不到。
   - 画板按图片快照处理：用 `docs +media-download` 下载画板缩略图，与普通图片一起重传，并向用户说明"画板已转为静态快照"。
   - 将图片逐张上传到临时文档，**每上传一张就记录 `{"source_token": "...", "file_token": "..."}` 映射**（media-insert 输出里有 file_token），汇总成 token map JSON。禁止只记顺序——重试一次顺序就错位。
   - 用 `scripts/assemble_markdown.py --plan ... --token-map ... --out ...` 生成最终 Markdown。脚本会校验映射完整性，缺映射会报错列出缺哪些 token；同时自动做两项平台适配：顶层块之间补空行（fetch 导出单换行紧凑格式，直接回灌 create 会把段落合并、结构错乱），callout 的 emoji 名称转为 emoji 字符（名称形式会让 callout 内全部行内样式解析失效）。
6. 创建文档（防截断）：
   - 用 `scripts/split_markdown.py --in final.md --out-dir /tmp/chunks` 安全分块（不会切断代码围栏和表格）。
   - 只有一块时直接 `docs +create`；多块时先 `docs +create` 首块，再按顺序 `docs +update --mode append` 追加其余块。
   - 附件类块（`<file>`）在文档创建后用 `docs +media-insert --doc <new_doc_id> --file <下载的附件> --type file` 重新插入（位置在文末，需向用户说明）。
7. 验证结果（不通过不得宣告成功）：
   - 重新 fetch 目标文档。
   - 运行 `scripts/compare_clone.py --source ... --final ... --expect-images <N>`，其中 N = 源图片数 + 已快照的画板数。
   - 脚本对代码块不一致、正文不一致（含截断，会定位首个分歧位置）、图片数不足**任一情况都会非零退出**。
   - 退出非零时必须排查修复或向用户报告具体缺口；`media_gaps` 中列出的电子表格、多维表等不可迁移块，要逐项告知用户原文位置和处理建议。

# 关键命令

盘点源文档块类型：

```bash
python3 scripts/inventory_blocks.py /tmp/source_blocks.json
```

拆分源文档：

```bash
python3 scripts/extract_plan.py \
  --fetch-json /tmp/source.json \
  --out /tmp/clone_plan.json
```

重组最终 Markdown（显式 token 映射）：

```bash
python3 scripts/assemble_markdown.py \
  --plan /tmp/clone_plan.json \
  --token-map /tmp/token_map.json \
  --out /tmp/final_clone.md
```

长文档安全分块：

```bash
python3 scripts/split_markdown.py \
  --in /tmp/final_clone.md \
  --out-dir /tmp/clone_chunks
```

比较源文档与副本（任一缺口非零退出）：

```bash
python3 scripts/compare_clone.py \
  --source /tmp/source.json \
  --final /tmp/final.json \
  --expect-images 5
```

# 已知平台转换限制（向用户如实说明，不算克隆失败）

- callout 的 `border-color` 属性：create API 不保留，副本只有背景色（compare 的 `style_diffs` 会列出）。
- callout 内**行首**的加粗（`**xx**` 在行首）：create API 会降级为字面 `**` 文本；行中加粗正常。需要严格保真时，可在创建后用 blocks PATCH 修复该文本块样式，或提示用户手动加粗。
- 电子表格、多维表、画板原件、未知类型块（fetch 中的 `<!-- Unsupported block type -->`）无法迁移；画板以静态图片快照代替。

# 注意事项

- 默认使用用户身份 `--as user`。
- 不打印 app secret、tenant token、图片下载签名或临时鉴权 URL。
- 不把源文档图片、下载文件、fetch JSON 或临时日志提交到 git。
- 图片无法直接下载时，优先使用浏览器可见内容提取；仍失败时说明缺口。
- 代码块内容必须保持精确，普通 Markdown 的空行和样式差异可以说明为平台转换差异。
- compare_clone 非零退出时禁止向用户宣告克隆成功；必须给出缺口清单（缺什么、为什么、建议怎么办）。
