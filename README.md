# 大模型学习助手 — 项目启动指南

> 一行命令启动完整前后端，从零到可用只要 5 分钟。

---

## 前置环境

| 依赖 | 最低版本 | 检查命令 |
|------|----------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

---

## 🚀 一键启动（推荐）

**Windows 用户双击 `start.bat` 即可**，自动完成 7 步环境检查与依赖安装：

| 步骤 | 检查/动作 |
|------|-----------|
| 1 | 检查 Node.js（18+） |
| 2 | 检查 Python（3.11+） |
| 3 | 创建/激活后端虚拟环境（`backend\.venv`） |
| 4 | 安装后端依赖（含 PaddleOCR / jieba / rank-bm25） |
| 5 | 检查 `backend\.env`，缺失则从 `.env.example` 复制并提示填 API Key |
| 6 | 安装前端依赖（`node_modules`） |
| 7 | 检查 8000/5173 端口 → 启动后端/前端 → 自动打开浏览器 |

**首次运行**：会弹出窗口提示 `LLM_API_KEY` 和 `EMBEDDING_API_KEY` 未配置。编辑 `backend\.env` 填入后再次双击 `start.bat` 即可（详见 [1.2 配置环境变量](#12-配置环境变量)）。

**启动成功标志**：
- 后端窗口标题 `AI-Study-Backend`，显示 `Running on http://0.0.0.0:8000`
- 前端窗口标题 `AI-Study-Frontend`，浏览器自动打开 `http://localhost:5173`
- 页面右上角状态指示器为绿色 = 启动正常

> 关闭启动器窗口**不会**停止服务，需单独关掉两个子窗口。

---

## 一、后端配置与启动

### 1.1 安装依赖

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

> **注意：** 如果 ChromaDB 安装报错 `Microsoft Visual C++ 14.0 is required`，执行：
>
> ```bash
> pip install chromadb --only-binary=chroma-hnswlib
> ```

### 1.2 配置环境变量

在 `backend/` 目录下创建 `.env` 文件（可复制 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
# ===== 必须配置 =====

# DeepSeek API Key（对话、出题、改卷、周报）
# 获取地址：https://platform.deepseek.com/api_keys
LLM_API_KEY=sk-your-deepseek-key

# 阿里云百炼 API Key（文档向量化与语义检索）
# 获取地址：https://bailian.console.aliyun.com/
EMBEDDING_API_KEY=sk-your-bailian-api-key

# ===== 可选配置 =====

# 运行环境（development / testing / production）
FLASK_ENV=development

# 数据库路径（默认 SQLite，无需额外安装）
DATABASE_URL=sqlite:///backend/data.db

# LLM 模型（默认 deepseek-chat）
LLM_MODEL_NAME=deepseek-chat

# Embedding 模型（默认 text-embedding-v4）
EMBEDDING_MODEL_NAME=text-embedding-v4

# 相似度阈值（0-1，低于此值的结果被过滤）
EMBEDDING_SIMILARITY_THRESHOLD=0.3

# ===== 混合检索（v0.3.0+，BM25 关键词 + 向量语义双路融合）=====
RETRIEVAL_MODE=hybrid              # dense（纯向量）| hybrid（默认）
DENSE_CANDIDATES=10                # 向量路候选数
BM25_CANDIDATES=10                 # 关键词路候选数
RRF_K=60                           # RRF 融合平滑参数
```

### 1.3 手动启动后端（不常用）

如需跳过 `start.bat` 一键启动直接跑后端：

```bash
# 进入 backend 目录，venv 已创建则可省略激活
cd backend
.venv\Scripts\python.exe run.py
```

启动成功会显示：

```
 * Running on http://0.0.0.0:8000
```

### 1.4 验证后端

新开终端，执行：

```bash
curl http://localhost:8000/api/v1/health
```

正常返回：

```json
{"code": 0, "data": {"status": "ok"}}
```

---

## 二、前端配置与启动

### 2.1 安装依赖

```bash
# 回到项目根目录
cd ..

# 安装依赖
npm install
```

### 2.2 启动前端

```bash
npm run dev
```

启动成功会显示：

```
VITE v6.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### 2.3 验证前端

浏览器打开 `http://localhost:5173/`，应看到导航栏包含 6 个 Tab：

**学习 | 资料库 | 测评 | 进度 | 报告 | 向量库**

右上角状态指示器（绿色圆点 = 后端已连接，红色 = 后端未启动）。

---

## 三、首次使用流程

### Step 1：上传资料

进入 **资料库** 页面 → 拖拽或点击上传 PDF / PPT / Word / Markdown / TXT 文件。

上传后状态显示 **解析中** → 后台自动解析文本、向量化存储 → 完成后变为 **完成**。

### Step 2：对话学习

进入 **学习** 页面 → 从下拉框选择已上传的资料（或保持"普通对话"）→ 输入问题，回车发送。

AI 基于资料内容回答，每条回答底部可展开查看引用来源。

### Step 3：测评

进入 **测评** 页面 → 选择资料范围和题数 → 点击"开始测评"→ 答题 → 提交。

AI 自动出题并批改，结果页展示分数、逐题解析和薄弱知识点。

### Step 4：查看进度

进入 **进度** 页面 → 查看统计卡片、雷达图、知识点掌握详情、笔记功能。

### Step 5：生成周报

进入 **报告** 页面 → 选择日期范围 → 点击"生成"→ 查看学习总结、薄弱环节与建议。

### Step 6：查看向量库（可选）

进入 **向量库** 页面 → 可视化查看知识块、文档块数分布、SQLite/ChromaDB 同步状态，支持按文档筛选和内容搜索。

---

## 四、项目结构速览

```
.
├── docs/                          # 文档
│   ├── requirements.md            # 功能需求文档
│   └── api-check-report.md        # 前后端接口一致性报告
├── src/                           # 前端源码 (React + TypeScript)
│   ├── pages/                     # 6 个页面（学习/资料库/测评/进度/报告/向量库）
│   ├── components/                # 通用组件（chat/quiz/charts/layout/common）
│   ├── api/client.ts              # API 请求封装
│   └── types/api.ts               # TypeScript 类型定义
├── backend/                       # 后端源码 (Python Flask)
│   ├── run.py                     # 启动入口
│   ├── .env.example               # 环境变量模板
│   ├── app/
│   │   ├── config.py              # 多环境配置
│   │   ├── models/models.py       # 10 张数据库表
│   │   ├── routes/                # 6 个路由（documents/chat/quiz/progress/report/vectordb）
│   │   └── services/              # 解析/分块/向量化/LLM/RAG/混合检索/OCR
│   ├── tests/                     # 24 个单元测试（chunker/keyword/hybrid）
│   └── requirements.txt           # Python 依赖
├── start.bat                      # Windows 一键启动（7 步自动检查）
├── rebuild_venv.bat               # 重建虚拟环境（可选）
└── package.json                   # 前端依赖
```

---

## 五、常见问题

### Q: 后端启动报 `LLM_API_KEY 未配置`

编辑 `backend/.env`，填入 `LLM_API_KEY` 和 `EMBEDDING_API_KEY`。

### Q: 上传资料后一直显示"解析中"

检查 `EMBEDDING_API_KEY` 是否正确配置。上传是异步后台处理，若密钥无效，资料状态会变为 **失败** 并显示错误信息。

### Q: 对话/出题报错

检查 `LLM_API_KEY` 是否正确，以及 DeepSeek 账户是否有可用余额。

### Q: 前端显示"服务断开"（红色圆点）

确认后端已启动（`python backend/run.py`），且端口为 8000。

### Q: 端口被占用

修改后端端口：编辑 `backend/run.py` 最后一行 `port=8000` 改为其他端口，同时修改前端 `vite.config.ts` 中 proxy target 的对应端口。

### Q: ChromaDB 安装失败 (Windows)

```bash
pip install chromadb --only-binary=chroma-hnswlib
```

### Q: PaddleOCR 安装失败 / 不想要 OCR 功能

PaddleOCR 是可选功能。安装失败可暂时移除 `requirements.txt` 中的 `paddlepaddle`、`paddleocr`、`opencv-python` 三行，**仅图片文字识别不可用**，其余功能（文档解析 / 对话 / 测评 / 进度 / 周报）正常工作。

### Q: 混合检索（BM25 + 向量）如何关闭？

编辑 `backend/.env`，设置 `RETRIEVAL_MODE=dense` 即可回退为纯向量检索（行为与 v0.2.x 一致）。重启后端生效。

### Q: 混合检索依赖（jieba / rank-bm25）未安装

执行项目根目录的 `install_hybrid_deps.bat` 即可（已改用相对路径，换机器/换目录都能跑），或手动：

```bash
cd backend
.venv\Scripts\activate
pip install jieba rank-bm25
```
