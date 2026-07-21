# 大模型学习助手 · AI Study Assistant

> 上传课程资料 → RAG 对话学习 → AI 自动出题测评 → 进度追踪 → 周报生成。面向自学者的完整学习闭环，一行命令启动。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Frontend: React 18](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg)](https://react.dev/)
[![Backend: Flask 3](https://img.shields.io/badge/Backend-Flask_3.1-000000.svg)](https://flask.palletsprojects.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Version: v0.3.1](https://img.shields.io/badge/Version-v0.3.1-2563eb.svg)](CHANGELOG.md)

---

## ✨ 功能亮点

### 完整的学习闭环

| 阶段 | 功能 | 亮点 |
|------|------|------|
| 📚 **资料导入** | 上传 PDF / PPT / Word / Markdown / TXT，自动解析分块向量化 | 支持 OCR 识别文档内嵌图片中的文字 |
| 💬 **智能问答** | 基于资料内容的 RAG 对话，回答可追溯引用来源 | 混合检索（BM25 + 向量 + RRF 融合），比纯向量检索命中率更高 |
| 📝 **自动测评** | AI 根据资料出题、批改、逐题解析 | 薄弱知识点自动诊断，精准定位学习短板 |
| 📊 **进度追踪** | 统计卡片、雷达图、知识点掌握度、笔记 | 量化学习成果，告别"感觉学到了但说不出" |
| 📅 **周报总结** | 选定日期范围，AI 自动生成学习总结与建议 | 定期复盘，结构化输出 |

### 工程亮点

- **混合检索（Hybrid Retrieval）**：BM25 关键词匹配 + 向量语义理解双路检索，RRF 融合无需调权，命中率和准确性远超纯向量方案
- **滑动窗口分块（Sliding Window Chunking）**：相邻 chunk 自动重叠 100 字符，保持语义连续性，避免"切断了关键段落"
- **本地 OCR**：PaddleOCR 离线识别 PDF/PPT/Word 中的图片文字，无需云端 API，隐私安全、零成本
- **对话历史持久化**：侧边栏管理历史会话，重命名/搜索/删除，新对话自动保存，不丢上下文
- **向量库可视化管理**：SQLite 块数 vs ChromaDB 向量数对比，同步状态指示，分档块数分布柱状图

---

## 🛠️ 技术栈

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│  Frontend: React 18 + TypeScript + Vite + Tailwind  │
│  (http://localhost:5173)                             │
└──────────────────────┬──────────────────────────────┘
                       │ REST / SSE
┌──────────────────────▼──────────────────────────────┐
│  Backend: Python Flask 3.1                           │
│  (http://localhost:8000)                             │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Document  │ │  Chunk   │ │   Hybrid Retrieval   │ │
│  │ Parser    │→│   Split  │→│ BM25 + Vector + RRF  │ │
│  │ (PyMuPDF) │ │ (Sliding │ │                      │ │
│  │ (pptx)    │ │  Window) │ │ DeepSeek ──→ Answer  │ │
│  │ (docx)    │ │          │ │                      │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│                                                      │
│  Embedding: 阿里云百炼 text-embedding-v4             │
│  Storage:   SQLite + ChromaDB (本地持久化)           │
│  OCR:       PaddleOCR (离线, 可选)                   │
└─────────────────────────────────────────────────────┘
```

### 技术选型与理由

| 层级 | 技术 | 为什么选它 |
|------|------|-----------|
| **前端框架** | React 18 + TypeScript | 组件化开发、类型安全；Vite 极速 HMR |
| **样式方案** | Tailwind CSS | 原子化 CSS，迭代快；Notion/ChatGPT 风格的现代简约 UI |
| **后端框架** | Python Flask 3.1 | 轻量无黑盒，学习友好；自动建表 + 蓝图模块化 |
| **ORM + 迁移** | SQLAlchemy + Flask-Migrate | 换数据库无需改代码；版本化 schema 变更 |
| **数据库** | SQLite | 零配置，本地文件，个人使用完全够，无需装 MySQL/PostgreSQL |
| **向量库** | ChromaDB（嵌入式） | 持久化到本地磁盘，无需单独部署服务 |
| **LLM** | DeepSeek `deepseek-chat` | 国产高性价比，兼容 OpenAI 协议，免费额度够学习 |
| **Embedding** | 阿里云百炼 `text-embedding-v4` | 1024 维中文语义向量，RAG 检索质量高 |
| **关键词检索** | jieba + rank-bm25 | 经典中文分词 + BM25 公式，纯内存零延迟 |
| **OCR** | PaddleOCR | 离线运行，图片不传云端，隐私安全 |
| **融合算法** | RRF (Reciprocal Rank Fusion) | k=60 标准值，双路分数量纲不同时仅排名可比 |

---

## 🚀 快速开始

### 前置环境

| 依赖 | 最低版本 | 检查命令 |
|------|----------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

### API Key（必须）

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| DeepSeek | 对话 / 出题 / 批改 / 周报 | <https://platform.deepseek.com/api_keys> |
| 阿里云百炼 | 文档向量化与语义检索 | <https://bailian.console.aliyun.com/> |

> 💡 两项服务均有免费额度，完全够个人学习使用。

### 方式一：一键启动（Windows 推荐）

**双击 `start.bat`**，自动完成全部 7 步：

| 步骤 | 动作 |
|------|------|
| 1 | 检查 Node.js（18+） |
| 2 | 检查 Python（3.11+） |
| 3 | 创建/激活后端虚拟环境（`backend\.venv`） |
| 4 | 安装后端依赖（Flask / ChromaDB / PaddleOCR / jieba / rank-bm25 等） |
| 5 | 检查 `backend\.env`，缺失则从模板复制并提示填 API Key |
| 6 | 安装前端依赖（`node_modules`） |
| 7 | 检查端口 → 启动后端/前端 → 自动打开浏览器 |

**首次运行** 会弹出窗口提示配置 API Key。编辑 `backend\.env` 填入后再次双击即可。

**启动成功标志**：
- 后端窗口标题 `AI-Study-Backend`，显示 `Running on http://0.0.0.0:8000`
- 前端窗口标题 `AI-Study-Frontend`，浏览器自动打开 `http://localhost:5173`
- 右上角状态指示器绿色 = 启动正常

> 关闭启动器窗口**不会**停止服务，需单独关掉两个子窗口。

### 方式二：手动启动（macOS / Linux / 自定义环境）

#### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
```

> ChromaDB 安装失败时执行：`pip install chromadb --only-binary=chroma-hnswlib`

从模板创建配置文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入你申请的 API Key：

```env
LLM_API_KEY=sk-your-deepseek-key
EMBEDDING_API_KEY=sk-your-bailian-api-key
```

启动后端：

```bash
python run.py
# Running on http://0.0.0.0:8000
```

验证：

```bash
curl http://localhost:8000/api/v1/health
# {"code": 0, "data": {"status": "ok"}}
```

#### 2. 前端

```bash
# 回到项目根目录
cd ..
npm install
npm run dev
# VITE v6.x.x ➜ http://localhost:5173/
```

浏览器打开 `http://localhost:5173/`，看到 6 个 Tab 即启动成功：

**学习 | 资料库 | 测评 | 进度 | 报告 | 向量库**

---

## 📁 项目结构

```
.
├── backend/
│   ├── run.py                          # 启动入口 (python run.py)
│   ├── .env.example                    # 环境变量模板
│   ├── requirements.txt                # Python 依赖
│   ├── app/
│   │   ├── config.py                   # 多环境配置 (dev / test / prod)
│   │   ├── models/models.py            # 10 张数据库表
│   │   ├── routes/                     # 6 个路由 (documents / chat / quiz / progress / report / vectordb)
│   │   └── services/                   # 核心业务
│   │       ├── parser.py               #     多格式文档解析
│   │       ├── chunker.py              #     滑动窗口分块
│   │       ├── embedding.py            #     向量化
│   │       ├── rag.py                  #     RAG 检索编排
│   │       ├── keyword_search.py       #     BM25 关键词检索
│   │       ├── hybrid_search.py        #     RRF 混合检索融合
│   │       ├── llm.py                  #     LLM 调用封装
│   │       └── ocr.py                  #     PaddleOCR 服务
│   ├── migrations/                     # 数据库迁移脚本
│   ├── tests/                          # 24 个单元测试
│   └── uploads/                        # 用户上传文件（运行时生成）
│
├── src/                                # 前端源码 (React + TypeScript)
│   ├── pages/                          # 6 个页面 (学习 / 资料库 / 测评 / 进度 / 报告 / 向量库)
│   ├── components/                     # 通用组件 (chat / quiz / charts / layout / common)
│   ├── api/client.ts                   # API 请求封装
│   └── types/api.ts                    # TypeScript 类型定义
│
├── docs/                               # 项目文档
├── start.bat                           # Windows 一键启动脚本
├── rebuild_venv.bat                    # 重建虚拟环境脚本
└── package.json                        # 前端依赖
```

---

## 📖 使用指南

### Step 1：上传资料

进入 **资料库** 页面 → 拖拽或点击上传 PDF / PPT / Word / Markdown / TXT。

状态显示 **解析中** → 后台自动分块、OCR（如有图片）、向量化 → 完成后变为 **完成**。

### Step 2：对话学习

进入 **学习** 页面 → 多选资料（支持同时引用多份文档）→ 输入问题，回车发送。

AI 基于资料内容回答，**每条回答底部可展开查看引用来源**（chunk_id + 文档名 + 页码）。

左侧侧边栏管理历史对话，支持重命名、搜索、删除。

### Step 3：自动测评

进入 **测评** 页面 → 选择资料范围和题数 → 点击 **开始测评** → 答题 → 提交。

AI 自动出题并批改，结果页展示分数、逐题解析和**薄弱知识点诊断**。

### Step 4：进度追踪

进入 **进度** 页面 → 查看统计卡片、雷达图、知识点掌握详情、个人笔记。

### Step 5：周报总结

进入 **报告** 页面 → 选择日期范围 → 点击 **生成** → 查看学习总结、薄弱环节与改进建议。

### Step 6：向量库管理（可选）

进入 **向量库** 页面 → 查看知识块列表、文档块数分布、SQLite/ChromaDB 同步状态，支持按文档筛选和内容搜索。

---

## ⚙️ 配置说明

所有配置通过 `backend/.env` 管理。完整模板见 `backend/.env.example`。

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | DeepSeek API Key（**必填**） | — |
| `LLM_MODEL_NAME` | 对话模型 | `deepseek-chat` |
| `EMBEDDING_API_KEY` | 百炼 API Key（**必填**） | — |
| `EMBEDDING_MODEL_NAME` | 向量模型 | `text-embedding-v4` |
| `EMBEDDING_SIMILARITY_THRESHOLD` | 相似度阈值 (0-1) | `0.3` |
| `RETRIEVAL_MODE` | 检索模式：`dense`（纯向量）/ `hybrid`（混合） | `hybrid` |
| `DENSE_CANDIDATES` | 向量路候选数 | `10` |
| `BM25_CANDIDATES` | 关键词路候选数 | `10` |
| `RRF_K` | RRF 融合平滑参数 | `60` |
| `CHUNK_SIZE` | 文本分块大小（字符） | `800` |
| `CHUNK_OVERLAP` | 分块重叠（字符） | `100` |
| `TOP_K_DEFAULT` | 返回来源条数 | `5` |
| `FLASK_ENV` | 运行环境 | `development` |

### 换用其他 LLM / Embedding

兼容 OpenAI 协议的服务均可替换：

```env
# 例：换成 OpenAI
LLM_API_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# 例：换成本地 Ollama
LLM_API_URL=http://localhost:11434/v1
LLM_MODEL_NAME=llama3
```

---

## 🙋 常见问题

<details>
<summary><b>上传资料后一直「解析中」</b></summary>

检查 `EMBEDDING_API_KEY` 是否配置正确。上传是异步后台处理，密钥无效时资料会变为「失败」并显示错误信息。
</details>

<details>
<summary><b>对话 / 出题报错</b></summary>

检查 `LLM_API_KEY` 是否正确，以及 DeepSeek 账户余额是否充足。
</details>

<details>
<summary><b>前端显示「服务断开」（红色圆点）</b></summary>

确认后端已启动（`python backend/run.py`），端口为 8000。
</details>

<details>
<summary><b>端口被占用</b></summary>

修改 `backend/run.py` 最后一行的 `port=8000`，同步改 `vite.config.ts` 中 proxy target 的端口。
</details>

<details>
<summary><b>ChromaDB 安装失败 (Windows)</b></summary>

```bash
pip install chromadb --only-binary=chroma-hnswlib
```
</details>

<details>
<summary><b>PaddleOCR 安装失败 / 不想要 OCR</b></summary>

PaddleOCR 是可选功能。移除 `requirements.txt` 中的 `paddlepaddle`、`paddleocr`、`opencv-python` 三行即可。**仅图片文字识别不可用**，其余功能正常。
</details>

<details>
<summary><b>混合检索如何关闭</b></summary>

设置 `RETRIEVAL_MODE=dense` 回退为纯向量检索（与 v0.2.x 一致），重启后端生效。
</details>

<details>
<summary><b>混合检索依赖未安装（jieba / rank-bm25）</b></summary>

这两个包已在 `requirements.txt` 中，`start.bat` 第 4 步自动安装。如需手动安装：

```bash
cd backend && .venv\Scripts\activate && pip install jieba rank-bm25
```
</details>

---

## 🤝 贡献指南

欢迎提 Issue 和 Pull Request。

1. **Fork** 本仓库
2. **创建特性分支**：`git checkout -b feature/xxx`
3. **提交并推送**：遵循 [Conventional Commits](https://www.conventionalcommits.org/)
4. **提交 Pull Request**：描述改动内容与动机

所有配置走环境变量，**不要硬编码 API Key**。数据库结构变更请用 Flask-Migrate 生成迁移脚本。

---

## 📜 开源协议

基于 [MIT License](LICENSE) 开源，可自由使用、修改、分发。

### 鸣谢

[DeepSeek](https://www.deepseek.com/) · [阿里云百炼](https://bailian.console.aliyun.com/) · [ChromaDB](https://www.trychroma.com/) · [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) · [React](https://react.dev/) · [Flask](https://flask.palletsprojects.com/) · [Vite](https://vitejs.dev/) · [Tailwind CSS](https://tailwindcss.com/)

---

## ⚠️ 安全提醒

- **切勿**将真实 API Key 提交到 Git 仓库
- `backend/.env` 已在 `.gitignore` 中排除，请只提交 `.env.example` 模板
- 生产环境部署时务必更换 `SECRET_KEY`，并设置 `FLASK_ENV=production`
- 上传的学习资料存储在本地 `backend/uploads/`，请注意数据备份

---

📅 版本变更记录见 [CHANGELOG.md](CHANGELOG.md)
