# Changelog

## v0.3.1 (2026-07-21)

### Bug 修复

#### TOP_K_DEFAULT 配置不生效
- 问题：`.env` 中 `TOP_K_DEFAULT` 被 `chat.py` 硬编码 `data.get('top_k', 5)` 绕过，修改后仍返回 5 条来源
- 修复：改为 `current_app.config.get('TOP_K_DEFAULT', 5)`，且前端未传 `top_k`，直接读配置

#### chat.py 缺少 current_app 导入
- 问题：修复 TOP_K_DEFAULT 时使用了 `current_app` 但未从 Flask 导入，导致 `NameError`
- 修复：`from flask import ... current_app ...`

#### BM25 相关度分数量纲不统一
- 问题：向量路 `relevance_score` 为余弦相似度（0~1），BM25 路为原始分数（0~∞），融合后两路量纲混乱，BM25 结果可能显示 >100% 的相关度
- 修复：`hybrid_search.py` 新增 `_normalize_relevance_scores()`，融合后统一按排名倒数归一化到 0~1（公式: `1/(1+0.2*rank)`）

### 修改文件

```
backend/app/routes/chat.py              — TOP_K_DEFAULT 读取方式 + 补 current_app import
backend/app/services/hybrid_search.py   — 新增 _normalize_relevance_scores()
```

---

## v0.3.0 (2026-07-21)

### 新增功能

#### 混合检索（Hybrid Retrieval）
- 检索层从纯向量单通道升级为 BM25 关键词 + Dense 向量双通道 + RRF 融合
- 新增 `keyword_search.py`：BM25Index 类，基于 jieba 分词 + rank-bm25 倒排索引，支持 build/add/remove/search
- 新增 `hybrid_search.py`：rrf_fuse() RRF 融合算法（k=60，无需调权）+ hybrid_search() 编排函数
- rag.py 检索入口从 `search_similar` 切换为 `hybrid_search`
- 启动时自动从 SQLite chunks 表全量重建 BM25 索引
- 文档上传/删除/重解析时同步维护 BM25 索引
- 检索召回数从 Top-5 提升为双路各 Top-10 → RRF 融合 → Top-5

#### 测试覆盖
- `test_keyword_search.py`：7 个 BM25 单元测试（索引/搜索/中文分词/增删/重建/边缘）
- `test_hybrid_search.py`：6 个 RRF + 编排测试（融合/退化/k 参数/编排回退）
- 存量 `test_chunker.py`：11 个用例全部通过
- 合计 24 个测试用例

### 配置变更

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RETRIEVAL_MODE` | `hybrid` | `dense`（纯向量）\| `hybrid`（混合，默认） |
| `DENSE_CANDIDATES` | `10` | 向量检索候选数 |
| `BM25_CANDIDATES` | `10` | 关键词检索候选数 |
| `RRF_K` | `60` | RRF 融合平滑参数 |

| 文件 | 变更 |
|------|------|
| `backend/requirements.txt` | 新增 `jieba>=0.42`、`rank-bm25>=0.2` |
| `backend/.env.example` | 新增混合检索参数注释 |
| `install_hybrid_deps.bat` | **新建** 一键安装混合检索依赖 |

### 技术细节

- 向后兼容：`RETRIEVAL_MODE=dense` 回退为纯向量模式，行为与 v0.2.x 完全一致
- RRF 融合无需调权，双路分数量纲不同时排名仍然可比
- BM25 索引维护：启动时全量重建 + 文档变更时增量同步
- 延迟影响：BM25 内存检索 < 5ms，远快于 Embedding API，总体延迟几乎不变
- Cross-Encoder 重排延后至 Phase 2

### 文件清单

```
新建文件 (4):
  backend/app/services/keyword_search.py    — BM25 关键词检索引擎
  backend/app/services/hybrid_search.py     — RRF 融合 + 混合检索编排
  backend/tests/test_keyword_search.py      — 7 个 BM25 单元测试
  backend/tests/test_hybrid_search.py       — 6 个 RRF + 编排测试

修改文件 (6):
  backend/app/services/rag.py               — 检索入口切换 hybrid_search
  backend/app/routes/documents.py           — 文档变更时维护 BM25 索引
  backend/app/__init__.py                   — 启动时重建 BM25 索引
  backend/app/config.py                     — 新增 4 个检索配置参数
  backend/requirements.txt                  — 新增 jieba, rank-bm25
  backend/.env.example                      — 新增混合检索参数注释
```

---

## v0.2.1 (2026-07-21)

### 新增功能

#### 学习页多资料对话
- 资料选择器从单选 `<select>` 升级为多选 `DocumentMultiSelect` 组件，支持同时引用多份资料进行 RAG 对话
- 组件：`src/components/chat/DocumentMultiSelect.tsx`（新建）
  - 触发按钮显示"选择资料"或"已选 N 份资料"
  - 已选资料以 chip 标签展示（最多 3 个 + 溢出折叠 `+N`）
  - Popover 下拉面板：搜索过滤 / 全选清空 / checkbox 列表 / 底部提示
  - 点击外部或按 Esc 关闭
- StudyPage 改动：
  - `selectedDocId: string` → `selectedDocIds: string[]`
  - `handleSend` 直接传 `selectedDocIds` 作为 `document_ids`
  - 空状态文案同步调整
- 后端零改动：`document_ids` API 参数和 ChromaDB `$in` 过滤自 v0.1.0 起已原生支持数组

### 配置变更

| 文件 | 变更 |
|------|------|
| `src/components/chat/DocumentMultiSelect.tsx` | **新建** 多选资料组件 |

### 文件清单

```
修改文件 (1):
  src/pages/StudyPage.tsx

新建文件 (1):
  src/components/chat/DocumentMultiSelect.tsx
```

---

## v0.2.0 (2026-07-21)

### 新增功能

#### 文本分块滑动窗口重叠（Overlap）
- `chunker.py` 实现真正的滑动窗口切分，相邻 chunk 之间保留上下文重叠区域
- 回顾式重叠机制：切块后从上一个 chunk 尾部提取 ~overlap_tokens 文本，拼接到下一个 chunk 开头，保持语义连续性
- `_split_long_paragraph`（语义分块主路径）：句子累积到阈值切断 → 取尾部 overlap → 拼到下一块起始
- `_hard_split`（超长句子硬切兜底）：步长从 `char_limit` 改为 `char_limit - overlap_chars`，字符级滑动窗口
- 跨页不做 overlap：页码是逻辑边界，避免不同页面的内容串入对方 chunk
- 守卫逻辑：`overlap >= chunk_size` 时自动退化为无 overlap 模式，不抛异常
- 短 chunk 兜底：上一个 chunk 比 overlap 还短时，有多少取多少

### 配置变更

| 文件 | 变更 |
|------|------|
| `backend/app/services/chunker.py` | 新增 `_extract_tail_tokens` + `_split_long_paragraph`/`_hard_split` 增加 `overlap_tokens` 参数 + `chunk_document` 传入 overlap |
| `backend/tests/test_chunker.py` | **新建** 11 个单元测试用例（覆盖正常路径 / 回归 / 边缘 / 集成） |

### 技术细节

- 默认参数不变：`CHUNK_SIZE=800, CHUNK_OVERLAP=100`（可通过 `.env` 调整）
- 不影响已有向量数据：仅对新上传/重新解析的文档生效
- 对 Embedding API 调用和存储量的影响：chunk 数量增加约 12.5%（100/800），可接受
- 测试运行：`cd backend && python -m pytest tests/test_chunker.py -v`（纯单元测试，无外部依赖）

### 文件清单

```
修改文件 (1):
  backend/app/services/chunker.py

新建文件 (1):
  backend/tests/test_chunker.py
```

---

## v0.1.0 (2026-07-20)

### 新增功能

#### 对话历史持久化与侧边栏
- 点击"新对话"时自动保存当前对话至后端，前端仅重置状态
- 左侧可折叠侧边栏（`ConversationSidebar`）展示历史对话列表，显示标题、相对时间戳、预览文本、消息数
- 支持点击历史记录恢复完整对话上下文和消息内容
- 支持重命名（内联编辑，Enter 确认 / Escape 取消）、删除（确认弹窗）、搜索过滤
- 新对话时弹出确认提示："当前对话将自动保存至历史记录"
- 流式响应进行中时切换会话或创建新对话自动 cancel 当前 SSE 连接
- 组件：`src/components/chat/ConversationSidebar.tsx`
- 后端：`PUT /api/v1/chat/sessions/{id}` 重命名端点 + `ChatSession.to_dict()` 含 `preview` 字段

#### 一键启动脚本
#### 一键启动脚本（已合并后端逻辑）
- `start.bat` — **唯一启动入口**，内置完整的后端环境搭建逻辑
  - 7 步环境检查：Node.js → Python → 虚拟环境 → 后端依赖 → 配置文件 → 前端依赖 → 端口占用
  - 主窗口自动创建 venv 并安装所有依赖（含 PaddleOCR），不再依赖外部脚本
  - 前后端在独立 `cmd` 窗口中启动，日志互不干扰
  - 端口检测：8000/5173 已监听时自动跳过，避免重复启动
  - 缺少 `.env` 时自动从 `.env.example` 复制并提示配置
  - 自动打开浏览器
- 已删除 `start-backend.bat`、`_install_deps.bat`（功能已合并）

#### 向量数据库管理后台
- 新增页面 `/vectordb`（导航栏"向量库"Tab）
- 左侧统计面板：Collection 名称、距离算法（cosine）、Embedding 模型、SQLite 块数 vs ChromaDB 向量数对比（含同步状态指示）、平均 token/块、各文档块数分布柱状图
- 右侧知识块表格：分页浏览、按文档筛选、内容模糊搜索、点击行展开完整文本 + 元数据（chunk_id、chroma_id、页码、章节标题）
- 后端 API：
  - `GET /api/v1/vectordb/stats` — 向量库全局统计
  - `GET /api/v1/vectordb/chunks` — 知识块分页列表
  - `GET /api/v1/vectordb/chunks/{id}` — 单个知识块详情
- 组件：`src/pages/VectorDBPage.tsx`
- 后端：`backend/app/routes/vectordb.py`

#### 本地 OCR 图片文字识别
- 新建 `backend/app/services/ocr.py` — 基于 PaddleOCR 的本地 OCR 服务
  - 懒加载模型（首次调用才初始化，不影响未使用该功能的场景）
  - 自动转换 CMYK/RGBA/P/灰度 → RGB
  - 小图过滤（< 50px 视为图标/装饰元素，自动跳过）
  - 逐张图片独立 try-catch，单张失败不影响其他图片和文档文本
  - PaddleOCR 未安装时静默跳过，不阻塞文档解析
- PDF 解析器集成：`page.get_images()` → `doc.extract_image()` 提取嵌入图片，OCR 结果追加到对应页文本后
- PPT 解析器集成：`shape.shape_type == 13` (Picture) → `shape.image.blob` 提取图片，结果追加到幻灯片文本后
- DOCX 解析器集成：`doc.part.rels` 中 `image` 类型提取图片 blob，结果追加到文档末尾
- 所有 OCR 结果以 `[图片内容]` 标记包裹，便于 RAG 检索时命中图片中的文字
- 新增依赖：`paddlepaddle>=2.6.0`、`paddleocr>=2.7.0`、`Pillow>=10.0`

### Bug 修复

#### 后端启动脚本路径错误
- 问题：`start-backend.bat` 中 `cd backend` 后 `%VPYTHON%` 相对路径 `backend\.venv\Scripts\python.exe` 解析为 `backend\backend\.venv\...`（路径不存在），导致"系统找不到指定的路径"
- 修复：删除 `cd backend` / `cd ..`，改为从项目根目录直接 `"%VPYTHON%" backend\run.py`

#### Vite 代理 ECONNREFUSED 终端刷屏
- 问题：前端启动后后端未就绪时，多个页面组件同时发起 API 请求，Vite 代理全部返回 `ECONNREFUSED`，终端被 `AggregateError` 堆栈持续刷屏
- 修复：`vite.config.ts` proxy 添加 `configure` 错误处理器，ECONNREFUSED 时 10 秒内最多输出一条黄色警告，不再打印完整堆栈

#### Word 文件上传失败
- 问题：`.doc`（旧版 Word 2003 格式）被映射到 `parse_docx` 使用 `python-docx` 打开，直接抛 `PackageNotFoundError`
- 问题：`parse_docx` 仅读取段落文本，表格内容完全丢失
- 问题：前端 `DocumentsPage` 仅显示"失败"标签，不展示 `error_message`
- 修复：
  - `.doc` 后缀检测 → 给出明确提示："不支持旧版 .doc 格式，请另存为 .docx 后重新上传"
  - `PackageNotFoundError` 捕获 → 友好提示
  - 新增表格文本提取（`doc.tables` → 每行 `|` 拼接）
  - 空文档检测并报错
  - 前端状态列 hover tooltip 展示完整 `error_message`

### 配置变更

| 文件 | 变更 |
|------|------|
| `backend/requirements.txt` | 新增 `paddlepaddle>=2.6.0`、`paddleocr>=2.7.0`、`Pillow>=10.0` |
| `vite.config.ts` | proxy 添加 `configure` ECONNREFUSED 抑制处理器 |
| `start-backend.bat` | 修复 `cd backend` 导致的路径错误 |
| `start.bat` | **新建** 一键启动脚本 |
| `_install_deps.bat` | **新建** 后端依赖安装脚本（含 PaddleOCR） |

### 文件清单

```
新建文件 (7):
  start.bat                             — 唯一启动入口（合并后端启动逻辑）
  CHANGELOG.md
  src/components/chat/ConversationSidebar.tsx
  src/pages/VectorDBPage.tsx
  backend/app/routes/vectordb.py
  backend/app/services/ocr.py

修改文件 (12):
  src/pages/StudyPage.tsx                — 集成侧边栏 + 会话管理
  src/pages/DocumentsPage.tsx            — 错误信息 tooltip
  src/api/client.ts                      — renameSession + vectorDB API
  src/types/api.ts                       — 新增类型定义
  src/App.tsx                            — /vectordb 路由
  src/components/layout/Navbar.tsx       — 向量库 Tab
  backend/app/__init__.py                — 注册 vectordb 蓝图
  backend/app/models/models.py           — ChatSession.to_dict 增加 preview
  backend/app/routes/chat.py             — PUT 重命名端点
  backend/app/services/parser.py         — Word 解析重写 + OCR 集成
  backend/requirements.txt               — OCR 依赖
  vite.config.ts                         — proxy 错误抑制

删除文件 (2):
  start-backend.bat                      — 功能已合并到 start.bat
  _install_deps.bat                      — 依赖安装已内置到 start.bat 第 4 步
```
