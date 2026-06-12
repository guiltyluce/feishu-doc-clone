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
   - 画板按图片快照处理：用 `docs +media-download --type whiteboard` 下载缩略图，**必须先用 `scripts/trim_snapshot.py` 裁掉空白边**（缩略图是固定 2560×2560 方图，内容只占一角，不裁会在文档里留大片空白），再与普通图片一起重传，并向用户说明"画板已转为静态快照"。
   - 书签卡片等 `unsupported_block` 块：用登录浏览器在源文档定位（DOM 类名如 `docx-bookmark-block`），提取链接和标题，构造 fills JSON（`[{"index": N, "markdown": "[标题](url)"}]`）传给 assemble 的 `--fills`，降级为可点击链接而不是直接丢弃。
   - **不要创建独立的暂存文档**——先用占位正文创建目标文档，用 `docs +media-insert --doc <目标doc_id>` 把图片直接传进目标文档，全程零额外文档。**每上传一张就记录 `{"source_token": "...", "file_token": "..."}` 映射**（输出里有 file_token 和 block_id，block_id 留作后续清理），汇总成 token map JSON。禁止只记顺序——重试一次顺序就错位。
   - 媒体所有权背景（已实测）：media-insert 的 token 属于宿主文档，宿主删除则 token 失效；而 create/append 摄入 `<image token>` 时会把媒体**复制**进目标文档并分配新 token。所以即便用了暂存文档，成品验证通过后暂存也可以删，但直接传目标文档更省事。
   - 用 `scripts/assemble_markdown.py --plan ... --token-map ... [--fills ...] --out ...` 生成最终 Markdown。脚本会校验映射完整性，缺映射会报错列出缺哪些 token；同时自动做三项平台适配：顶层块之间补空行（fetch 导出单换行紧凑格式，直接回灌 create 会把段落合并、结构错乱），callout 的 emoji 名称转为 emoji 字符（名称形式会让 callout 内全部行内样式解析失效），callout 的 `border-color="light-X"` 转为 `"X"`（create 会静默丢弃 light 值导致副本没边框）。
6. 写入正文（防截断）：
   - 用 `scripts/split_markdown.py --in final.md --out-dir /tmp/chunks` 安全分块（不会切断代码围栏和表格）。
   - 按顺序 `docs +update --mode append` 把各块追加到第 5 步创建的目标文档。
   - 正文写完后，用 blocks `children/batch_delete` 删掉文档开头的占位正文块和 media-insert 留下的多余媒体块（同文档内删块不影响 token 存活，已验证）。
   - 附件类块（`<file>`）在文档创建后用 `docs +media-insert --doc <new_doc_id> --file <下载的附件> --type file` 重新插入（位置在文末，需向用户说明）。
   - 创建完成后**必须**运行 `scripts/repair_styles.py --source-blocks <源blocks.json> --doc <新doc_id>` 修复平台 bug：callout 内行首加粗会被 create 降级为字面 `**` 并把相邻行合并成一个块；脚本会按源块逐一 PATCH 样式、拆开被合并的块。
7. 验证结果（不通过不得宣告成功）：
   - 重新 fetch 目标文档。
   - 运行 `scripts/compare_clone.py --source ... --final ... --expect-images <N> [--fills ...]`，其中 N = 源图片数 + 已快照的画板数；用了 fills 时必须把同一份 fills 传给 compare（填充的链接文本属于刻意新增）。
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

- 电子表格、多维表、画板原件无法迁移；画板以静态图片快照代替（已裁边），书签卡片降级为普通链接（预览卡片样式丢失，用户可在 UI 中手动切回卡片视图）。
- callout 行首加粗、border-color、emoji、段落合并等 create API 缺陷已由 assemble 预处理 + repair_styles 后处理自动修复，无需人工干预；如 repair_styles 报 skipped，需把未修复块明确告知用户。

# 注意事项

- 默认使用用户身份 `--as user`。
- **不留噪音**：整个流程只产生最终文档这一个产物。验证失败需要重建时，先用 `lark-cli api DELETE /open-apis/drive/v1/files/<doc_id> --params '{"type":"docx"}'` 删除废弃文档再重走流程；成品的媒体在 create 时已复制为自有 token，删除中间文档不影响成品（已验证）。调试性试验一律不建真实文档，确需建的用 `[mini]` 前缀并当场删除。
- 不打印 app secret、tenant token、图片下载签名或临时鉴权 URL。
- 不把源文档图片、下载文件、fetch JSON 或临时日志提交到 git。
- 图片无法直接下载时，优先使用浏览器可见内容提取；仍失败时说明缺口。
- 代码块内容必须保持精确，普通 Markdown 的空行和样式差异可以说明为平台转换差异。
- compare_clone 非零退出时禁止向用户宣告克隆成功；必须给出缺口清单（缺什么、为什么、建议怎么办）。
