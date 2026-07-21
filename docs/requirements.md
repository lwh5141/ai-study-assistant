# 大模型学习助手 — 功能需求文档

> 版本：v1.0 | 日期：2026-07-19 | 状态：设计阶段（待确认后开发）

---

## 一、功能拆解与优先级

### 1. 传资料

| 编号 | 子功能 | 优先级 | 说明 |
|------|--------|--------|------|
| U-01 | 文件上传（拖拽/选择） | **P0** | 支持 `.pdf`、`.ppt`/`.pptx`、`.md`、`.txt` 、`.doc`/`.docx` 多种格式，前端校验文件类型与大小（上限 50MB），单次可上传多个文件 |
| U-02 | PDF 文本解析 | **P0** | PyMuPDF 提取文本，保留页码信息，过滤页眉页脚噪音 |
| U-03 | PPT 文本解析 | **P0** | python-pptx 提取每页幻灯片文本，保留页号与标题层级 |
| U-04 | Markdown 文本解析 | **P0** | 按标题层级拆分，保留结构信息 |
| U-05 | Word 文本解析 | **P0** | python-docx 提取 .docx 文件文本，保留段落与标题结构；.doc 文件需先转为 .docx 再解析 |
| U-06 | TXT 文本解析 | **P0** | 按自然段落拆分纯文本文件，编码自动检测（UTF-8/GBK），保留段落边界 |
| U-07 | 文本分块 (Chunking) | **P0** | 按语义段落分割（非固定字数截断），每块 500–1000 tokens，相邻块重叠 100 tokens；保留来源文件名、页码/章节等元数据 |
| U-08 | 向量化与存储 | **P0** | BGE-M3 模型生成 Embedding，存入 ChromaDB，返回 chunk_id 与向量索引 |
| U-09 | 资料列表管理 | **P0** | 查看已上传资料列表（名称、类型、大小、上传时间、解析状态）、支持删除单个资料（级联删除其 chunk 与向量） |
| U-10 | 上传进度反馈 | **P1** | 实时展示解析→分块→向量化各阶段进度 |
| U-11 | 重复上传检测 | **P1** | 基于文件名+文件哈希判断是否已存在，支持"覆盖"或"跳过" |
| U-12 | 批量上传队列 | **P1** | 同时上传多个文件时排队处理，展示队列状态 |

### 2. 聊资料

| 编号 | 子功能 | 优先级 | 说明 |
|------|--------|--------|------|
| C-01 | 对话界面 | **P0** | 消息气泡式聊天 UI，支持打字动画/流式输出 |
| C-02 | 语义检索 | **P0** | 用户问题→BGE-M3 向量化→ChromaDB 检索 top-k（默认 k=5，可配置）相关文本 chunk |
| C-03 | RAG 回答生成 | **P0** | 检索结果拼接为 Context，与用户问题一起送入 LLM，生成带引用的回答 |
| C-04 | 资料来源标注 | **P0** | 每条回答末尾或内联标注引用来源，格式：`📎 来源：《XXX.pdf》第3页`，前端点击可展开原文片段 |
| C-05 | 对话历史 | **P0** | 持久化保存对话记录，支持查看历史、继续对话 |
| C-06 | 多轮对话上下文 | **P1** | 保留最近 N=10 轮对话作为上下文，追问时携带历史 |
| C-07 | 无资料提示 | **P1** | 未上传任何资料时，引导用户先上传再对话 |
| C-08 | 新建/切换对话 | **P1** | 支持新建会话、切换历史会话、删除会话 |

### 3. 做测评

| 编号 | 子功能 | 优先级 | 说明 |
|------|--------|--------|------|
| Q-01 | 自动生成题目 | **P0** | LLM 基于已上传资料的知识点生成题目；题型：单选题、判断题、简答题 |
| Q-02 | 答题界面 | **P0** | 逐题展示或整卷展示，支持上一题/下一题导航、答题进度条、倒计时（可选） |
| Q-03 | 自动判分 | **P0** | 选择题/判断题自动对比标准答案；简答题由 LLM 按 0/0.5/1 三档评分 |
| Q-04 | 结果与解析 | **P0** | 展示总分、正确率、逐题解析（正确答案 + 知识点说明 + 资料来源），标注薄弱知识点 |
| Q-05 | 题量与范围配置 | **P1** | 用户可自定义题目数量（默认 10 题）、出题范围（全部/指定资料） |
| Q-06 | 错题本 | **P1** | 自动收集答错的题目，支持按知识点分类查看、重新练习错题 |
| Q-07 | 测评历史 | **P1** | 列表展示历史测评记录（时间、分数、范围），点击可查看详情 |

### 4. 看进度

| 编号 | 子功能 | 优先级 | 说明 |
|------|--------|--------|------|
| P-01 | 资料概览卡片 | **P0** | 已上传资料数量、总大小、最后上传时间 |
| P-02 | 测评历史列表 | **P0** | 展示历次测评的时间、分数、题目数、涉及资料 |
| P-03 | 正确率趋势图 | **P1** | 折线图展示近期测评正确率变化趋势 |
| P-04 | 知识点掌握热力图 | **P1** | 按资料/章节维度展示掌握程度（颜色深浅），从测评结果反向推算 |
| P-05 | 学习天数统计 | **P1** | 打卡日历，展示最近 30 天的活跃情况 |

### 5. 出周报

| 编号 | 子功能 | 优先级 | 说明 |
|------|--------|--------|------|
| R-01 | 周报生成 | **P0** | LLM 汇总本周学习数据，自动生成结构化周报（学习时长、上传资料、测评成绩、薄弱知识点 Top 3、学习建议） |
| R-02 | 周报查看 | **P1** | 历史周报列表，支持按周切换查看 |
| R-03 | 周报导出 | **P1** | 支持导出为 Markdown 或 PDF |

---

## 二、后台接口设计

> 基础路径：`/api/v1`

### 2.1 资料管理

#### `POST /api/v1/documents/upload`

上传文件并触发解析、分块、向量化流水线。

**请求：** `multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 上传文件，支持 pdf/ppt/pptx/md/doc/docx/txt，最大 50MB |
| overwrite | bool | 否 | 同名文件是否覆盖，默认 false |

**响应：** `201 Created`

```json
{
  "code": 0,
  "data": {
    "id": "doc_abc123",
    "filename": "Transformer原理详解.pdf",
    "file_type": "pdf",
    "file_size": 2456789,
    "status": "processing",
    "chunk_count": 0,
    "created_at": "2026-07-19T12:00:00Z"
  }
}
```

**状态码：** 201 成功 | 400 格式不支持 | 409 文件已存在 | 413 文件过大 | 500 解析失败

---

#### `GET /api/v1/documents`

获取已上传资料列表。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |
| status | string | 否 | 筛选状态：processing/ready/error |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "total": 12,
    "items": [
      {
        "id": "doc_abc123",
        "filename": "Transformer原理详解.pdf",
        "file_type": "pdf",
        "file_size": 2456789,
        "status": "ready",
        "chunk_count": 34,
        "created_at": "2026-07-19T12:00:00Z"
      }
    ]
  }
}
```

---

#### `GET /api/v1/documents/{document_id}`

获取单个资料详情。

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "id": "doc_abc123",
    "filename": "Transformer原理详解.pdf",
    "file_type": "pdf",
    "file_size": 2456789,
    "status": "ready",
    "chunk_count": 34,
    "created_at": "2026-07-19T12:00:00Z",
    "updated_at": "2026-07-19T12:01:30Z"
  }
}
```

**状态码：** 200 成功 | 404 资料不存在

---

#### `DELETE /api/v1/documents/{document_id}`

删除资料及其关联的 chunk、向量数据、测评中的引用。

**响应：** `200 OK`

```json
{
  "code": 0,
  "message": "删除成功（已清理 34 个文本块和 34 条向量数据）"
}
```

**状态码：** 200 成功 | 404 资料不存在

---

### 2.2 对话问答

#### `POST /api/v1/chat`

发送消息，执行 RAG 检索并返回 AI 回答。支持 SSE 流式输出。

**请求：** `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 否 | 会话 ID，不传则新建会话 |
| message | string | 是 | 用户问题，最大 2000 字符 |
| document_ids | string[] | 否 | 限定检索范围（资料 ID 列表），不传则检索全部 |
| top_k | int | 否 | 检索数量，默认 5 |

**响应（非流式）：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_xyz789",
    "message_id": "msg_001",
    "role": "assistant",
    "content": "Transformer 的核心创新在于完全摒弃了循环结构，转而使用自注意力（Self-Attention）机制来捕获序列中任意两个位置之间的依赖关系……",
    "sources": [
      {
        "document_id": "doc_abc123",
        "document_name": "Transformer原理详解.pdf",
        "page": 3,
        "chunk_index": 5,
        "excerpt": "自注意力机制的计算公式为 Attention(Q,K,V) = softmax(QK^T/√d_k)V……",
        "relevance_score": 0.92
      }
    ],
    "created_at": "2026-07-19T14:30:00Z"
  }
}
```

**流式响应：** `Accept: text/event-stream`，逐 token 推送，最后一条消息附带 sources 字段。

**状态码：** 200 成功 | 400 消息为空 | 422 无可用资料

---

#### `GET /api/v1/chat/sessions`

获取对话会话列表。

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": [
    {
      "session_id": "sess_xyz789",
      "title": "关于Transformer自注意力机制",
      "message_count": 6,
      "created_at": "2026-07-19T14:30:00Z",
      "updated_at": "2026-07-19T14:45:00Z"
    }
  ]
}
```

---

#### `GET /api/v1/chat/sessions/{session_id}`

获取指定会话的完整消息历史。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 50 |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_xyz789",
    "title": "关于Transformer自注意力机制",
    "messages": [
      {
        "message_id": "msg_001",
        "role": "user",
        "content": "Transformer的自注意力机制怎么理解？",
        "created_at": "2026-07-19T14:30:00Z"
      },
      {
        "message_id": "msg_002",
        "role": "assistant",
        "content": "……",
        "sources": [],
        "created_at": "2026-07-19T14:30:05Z"
      }
    ]
  }
}
```

---

#### `DELETE /api/v1/chat/sessions/{session_id}`

删除指定会话及其所有消息。

**响应：** `200 OK`

```json
{ "code": 0, "message": "会话已删除" }
```

---

### 2.3 测评

#### `POST /api/v1/quiz/generate`

基于资料内容自动生成一套测评题。

**请求：** `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 测评标题，默认自动生成 |
| question_count | int | 否 | 题目总数，默认 10，范围 5–30 |
| document_ids | string[] | 否 | 限定出题范围，不传则覆盖全部资料 |
| question_types | string[] | 否 | 题型组合，默认 ["choice","true_false","short_answer"] |

**响应：** `201 Created`

```json
{
  "code": 0,
  "data": {
    "quiz_id": "quiz_001",
    "title": "Transformer 核心原理测评",
    "question_count": 10,
    "status": "ready",
    "questions": [
      {
        "question_id": "q_001",
        "index": 1,
        "type": "choice",
        "content": "在 Transformer 中，自注意力机制计算时除以 √d_k 的目的是什么？",
        "options": [
          {"key": "A", "text": "增加梯度，加速收敛"},
          {"key": "B", "text": "防止点积过大导致 softmax 梯度消失"},
          {"key": "C", "text": "减少计算量"},
          {"key": "D", "text": "提高模型容量"}
        ],
        "correct_answer": "B",
        "explanation": "除以 √d_k 是为了缩放点积结果，防止值过大时 softmax 进入饱和区，导致梯度消失。",
        "source_document": "Transformer原理详解.pdf",
        "source_page": 5
      }
    ],
    "created_at": "2026-07-19T15:00:00Z"
  }
}
```

> **注意：** 首次请求返回题目时 **不包含** `correct_answer` 和 `explanation` 字段，仅在提交答案后的结果接口中返回。

**状态码：** 201 成功 | 422 无可用资料 | 400 参数无效

---

#### `POST /api/v1/quiz/{quiz_id}/submit`

提交测评答案，触发判分。

**请求：** `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| answers | object[] | 是 | 答案列表 |
| answers[].question_id | string | 是 | 题目 ID |
| answers[].answer | string | 是 | 用户答案（选择题填选项字母，判断题填 true/false，简答题填文本） |

**请求示例：**

```json
{
  "answers": [
    {"question_id": "q_001", "answer": "B"},
    {"question_id": "q_002", "answer": "true"},
    {"question_id": "q_003", "answer": "位置编码的作用是为模型提供序列中token的位置信息，因为自注意力机制本身不具备位置感知能力。"}
  ]
}
```

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "quiz_id": "quiz_001",
    "total_score": 85,
    "correct_count": 8,
    "total_count": 10,
    "accuracy": 0.80,
    "details": [
      {
        "question_id": "q_001",
        "index": 1,
        "type": "choice",
        "content": "在 Transformer 中，自注意力机制计算时除以 √d_k 的目的是什么？",
        "user_answer": "B",
        "correct_answer": "B",
        "is_correct": true,
        "score": 1,
        "explanation": "除以 √d_k 是为了缩放点积结果，防止值过大时 softmax 进入饱和区，导致梯度消失。",
        "source_document": "Transformer原理详解.pdf",
        "source_page": 5
      }
    ],
    "weak_points": [
      {
        "knowledge_point": "多头注意力机制",
        "document": "Transformer原理详解.pdf",
        "error_count": 2
      }
    ],
    "submitted_at": "2026-07-19T15:30:00Z"
  }
}
```

**状态码：** 200 成功 | 400 参数无效 | 404 测评不存在 | 409 已提交过

---

#### `GET /api/v1/quiz/{quiz_id}/result`

获取已提交测评的结果详情（结构同提交返回，可重复查看）。

**响应：** 同 `POST .../submit`

**状态码：** 200 成功 | 404 测评不存在 | 422 尚未提交

---

#### `GET /api/v1/quiz/history`

获取测评历史列表。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 默认 1 |
| page_size | int | 否 | 默认 10 |
| status | string | 否 | ready/submitted |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "total": 5,
    "items": [
      {
        "quiz_id": "quiz_001",
        "title": "Transformer 核心原理测评",
        "question_count": 10,
        "status": "submitted",
        "score": 85,
        "accuracy": 0.80,
        "created_at": "2026-07-19T15:00:00Z",
        "submitted_at": "2026-07-19T15:30:00Z"
      }
    ]
  }
}
```

---

#### `GET /api/v1/quiz/wrong-questions`

获取错题本列表。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| document_id | string | 否 | 按资料筛选 |
| page | int | 否 | 默认 1 |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "total": 8,
    "items": [
      {
        "question_id": "q_005",
        "quiz_id": "quiz_001",
        "type": "choice",
        "content": "……",
        "user_answer": "A",
        "correct_answer": "B",
        "explanation": "……",
        "source_document": "Transformer原理详解.pdf",
        "created_at": "2026-07-19T15:00:00Z"
      }
    ]
  }
}
```

---

### 2.4 学习进度

#### `GET /api/v1/progress/overview`

获取学习进度概览数据。

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "total_documents": 12,
    "total_quizzes": 5,
    "total_quiz_questions": 50,
    "avg_accuracy": 0.82,
    "study_days_this_week": 3,
    "total_chunks": 340,
    "last_activity": "2026-07-19T15:30:00Z"
  }
}
```

---

#### `GET /api/v1/progress/knowledge`

获取知识点掌握情况。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| document_id | string | 否 | 限定资料 |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": [
    {
      "knowledge_point": "自注意力机制",
      "document_name": "Transformer原理详解.pdf",
      "mastery_level": 0.85,
      "total_questions": 4,
      "correct_count": 3,
      "last_tested": "2026-07-18T10:00:00Z"
    },
    {
      "knowledge_point": "多头注意力机制",
      "document_name": "Transformer原理详解.pdf",
      "mastery_level": 0.33,
      "total_questions": 3,
      "correct_count": 1,
      "last_tested": "2026-07-19T15:30:00Z"
    }
  ]
}
```

---

### 2.5 周报

#### `POST /api/v1/report/generate`

生成指定周的周报。

**请求：** `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| week_start | string | 否 | 周一日期 (YYYY-MM-DD)，默认本周一 |
| week_end | string | 否 | 周日日期 (YYYY-MM-DD)，默认本周日 |

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "id": "rpt_001",
    "week_start": "2026-07-13",
    "week_end": "2026-07-19",
    "content": {
      "summary": "本周学习总时长约 5.2 小时，上传 3 份新资料，完成 2 次测评……",
      "study_time_hours": 5.2,
      "new_documents": 3,
      "quiz_count": 2,
      "avg_score": 82.5,
      "accuracy_trend": "上升 (+5%)",
      "weak_points": [
        {"point": "多头注意力机制", "accuracy": 0.33, "suggestion": "建议重点复习 Transformer 原论文 Section 3.2.2"},
        {"point": "Layer Normalization", "accuracy": 0.50, "suggestion": "建议对比 Batch Norm 与 Layer Norm 的区别，关注 NLP 场景下 Layer Norm 的优势"}
      ],
      "weekly_suggestion": "下周建议将多头注意力机制和 Layer Normalization 作为重点复习内容，可以上传相关补充材料后进行针对性测评。"
    },
    "generated_at": "2026-07-19T20:00:00Z"
  }
}
```

---

#### `GET /api/v1/report/list`

获取周报列表。

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": [
    {
      "id": "rpt_001",
      "week_start": "2026-07-13",
      "week_end": "2026-07-19",
      "avg_score": 82.5,
      "quiz_count": 2,
      "generated_at": "2026-07-19T20:00:00Z"
    }
  ]
}
```

---

#### `GET /api/v1/report/{report_id}`

获取周报详情。响应结构与生成接口返回一致。

---

### 2.6 系统设置

#### `GET /api/v1/settings`

获取当前系统设置。

**响应：** `200 OK`

```json
{
  "code": 0,
  "data": {
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "embedding_model": "BAAI/bge-m3",
    "chunk_size": 800,
    "chunk_overlap": 100,
    "top_k_default": 5
  }
}
```

---

#### `PUT /api/v1/settings`

更新系统设置。

**请求：** `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| openai_api_key | string | 否 | OpenAI API Key |
| openai_base_url | string | 否 | 自定义 API 端点（兼容其他 provider） |
| llm_model | string | 否 | 模型名称 |
| chunk_size | int | 否 | 分块大小 (tokens) |

**响应：** `200 OK`，返回更新后的完整设置。

---

## 三、数据库表设计

> 数据库引擎：SQLite（单文件，零配置，适合单机使用）

### 3.1 `documents` — 资料表

存储已上传资料的基本信息。

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `doc_{uuid8}` |
| filename | TEXT | 是 | — | 原始文件名 |
| file_type | TEXT | 是 | — | 文件类型：pdf / ppt / pptx / md / doc / docx / txt |
| file_size | INTEGER | 是 | 0 | 文件大小（字节） |
| file_path | TEXT | 是 | — | 服务器本地存储路径 |
| file_hash | TEXT | 否 | NULL | SHA-256，用于去重 |
| status | TEXT | 是 | 'processing' | processing / ready / error |
| chunk_count | INTEGER | 是 | 0 | 分块数量 |
| error_message | TEXT | 否 | NULL | 解析失败时的错误信息 |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 上传时间 (ISO 8601) |
| updated_at | TEXT | 是 | CURRENT_TIMESTAMP | 最后更新时间 |

**索引：**
- 主键：`id`
- 普通索引：`idx_documents_status` ON (`status`)
- 普通索引：`idx_documents_file_hash` ON (`file_hash`)
- 普通索引：`idx_documents_created_at` ON (`created_at`)

---

### 3.2 `chunks` — 文本块表

存储解析后的文本分块及其元数据。

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `chk_{uuid8}` |
| document_id | TEXT | 是 | — | 外键 → `documents.id`，级联删除 |
| chunk_index | INTEGER | 是 | — | 块在文档内的序号（0 起始） |
| content | TEXT | 是 | — | 文本内容 |
| chroma_id | TEXT | 是 | — | ChromaDB 中对应向量的 ID |
| page_number | INTEGER | 否 | NULL | 来源页码（PDF/PPT） |
| section_title | TEXT | 否 | NULL | 所属章节标题 |
| token_count | INTEGER | 否 | NULL | 近似 token 数量 |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- 主键：`id`
- 外键：`document_id` REFERENCES `documents(id)` ON DELETE CASCADE
- 普通索引：`idx_chunks_document_id` ON (`document_id`)
- 普通索引：`idx_chunks_chroma_id` ON (`chroma_id`)

---

### 3.3 `chat_sessions` — 对话会话表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `sess_{uuid8}` |
| title | TEXT | 否 | '新对话' | 会话标题（自动截取首条消息） |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TEXT | 是 | CURRENT_TIMESTAMP | 最后活跃时间 |

**索引：**
- 主键：`id`
- 普通索引：`idx_chat_sessions_updated_at` ON (`updated_at`)

---

### 3.4 `chat_messages` — 对话消息表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `msg_{uuid8}` |
| session_id | TEXT | 是 | — | 外键 → `chat_sessions.id` |
| role | TEXT | 是 | — | user / assistant |
| content | TEXT | 是 | — | 消息内容 |
| sources | TEXT | 否 | '[]' | JSON 数组，引用来源列表 |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 发送时间 |

**索引：**
- 主键：`id`
- 外键：`session_id` REFERENCES `chat_sessions(id)` ON DELETE CASCADE
- 普通索引：`idx_chat_messages_session_id` ON (`session_id`)

---

### 3.5 `quizzes` — 测评记录表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `quiz_{uuid8}` |
| title | TEXT | 是 | — | 测评标题 |
| question_count | INTEGER | 是 | 10 | 题目总数 |
| document_ids | TEXT | 否 | '[]' | JSON 数组，出题范围（资料 ID 列表） |
| status | TEXT | 是 | 'ready' | ready / submitted |
| total_score | REAL | 否 | NULL | 总分（百分制），提交后填入 |
| correct_count | INTEGER | 否 | NULL | 正确数量 |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 生成时间 |
| submitted_at | TEXT | 否 | NULL | 提交时间 |

**索引：**
- 主键：`id`
- 普通索引：`idx_quizzes_status` ON (`status`)
- 普通索引：`idx_quizzes_created_at` ON (`created_at`)

---

### 3.6 `quiz_questions` — 测评题目表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `q_{uuid8}` |
| quiz_id | TEXT | 是 | — | 外键 → `quizzes.id` |
| question_index | INTEGER | 是 | — | 题号（1 起始） |
| type | TEXT | 是 | — | choice / true_false / short_answer |
| content | TEXT | 是 | — | 题目内容 |
| options | TEXT | 否 | '[]' | JSON 数组，选择题选项 `[{"key":"A","text":"..."}]` |
| correct_answer | TEXT | 是 | — | 标准答案 |
| explanation | TEXT | 否 | NULL | 答案解析 |
| source_document_id | TEXT | 否 | NULL | 来源资料 ID |
| source_chunk_id | TEXT | 否 | NULL | 来源文本块 ID |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- 主键：`id`
- 外键：`quiz_id` REFERENCES `quizzes(id)` ON DELETE CASCADE
- 普通索引：`idx_quiz_questions_quiz_id` ON (`quiz_id`)

---

### 3.7 `quiz_answers` — 答题记录表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `ans_{uuid8}` |
| quiz_id | TEXT | 是 | — | 外键 → `quizzes.id` |
| question_id | TEXT | 是 | — | 外键 → `quiz_questions.id` |
| user_answer | TEXT | 是 | — | 用户答案 |
| is_correct | INTEGER | 否 | NULL | 是否正确（0/1），简答题可为 NULL（视为部分正确） |
| score | REAL | 否 | NULL | 该题得分（0/0.5/1.0） |
| submitted_at | TEXT | 是 | CURRENT_TIMESTAMP | 提交时间 |

**索引：**
- 主键：`id`
- 外键：`quiz_id` REFERENCES `quizzes(id)` ON DELETE CASCADE
- 外键：`question_id` REFERENCES `quiz_questions(id)` ON DELETE CASCADE
- 唯一索引：`uq_quiz_answers_question` ON (`quiz_id`, `question_id`)

---

### 3.8 `knowledge_points` — 知识点掌握表

基于测评结果自动更新的知识点掌握状态。

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `kp_{uuid8}` |
| name | TEXT | 是 | — | 知识点名称（如"多头注意力机制"） |
| document_id | TEXT | 是 | — | 外键 → `documents.id` |
| total_questions | INTEGER | 是 | 0 | 累计相关题数 |
| correct_count | INTEGER | 是 | 0 | 累计正确数 |
| mastery_level | REAL | 是 | 0.0 | 掌握程度 (0.0–1.0) |
| last_tested_at | TEXT | 否 | NULL | 最近测评时间 |
| created_at | TEXT | 是 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TEXT | 是 | CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- 主键：`id`
- 外键：`document_id` REFERENCES `documents(id)` ON DELETE CASCADE
- 唯一索引：`uq_knowledge_points_name_doc` ON (`name`, `document_id`)

---

### 3.9 `weekly_reports` — 周报表

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | TEXT | 是 | — | 主键，格式 `rpt_{uuid8}` |
| week_start | TEXT | 是 | — | 周一日期 (YYYY-MM-DD) |
| week_end | TEXT | 是 | — | 周日日期 (YYYY-MM-DD) |
| content_json | TEXT | 是 | — | 周报完整 JSON |
| generated_at | TEXT | 是 | CURRENT_TIMESTAMP | 生成时间 |

**索引：**
- 主键：`id`
- 唯一索引：`uq_weekly_reports_week` ON (`week_start`, `week_end`)

---

### 3.10 `settings` — 系统设置表

Key-Value 结构，灵活扩展。

| 字段 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| key | TEXT | 是 | — | 主键，设置项名称 |
| value | TEXT | 是 | — | 设置值（JSON 或纯文本） |
| updated_at | TEXT | 是 | CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- 主键：`key`

---

### ER 关系图（文字描述）

```
documents 1 ──── N chunks
documents 1 ──── N knowledge_points
documents ────── quizzes (多对多，通过 document_ids JSON 关联)
quizzes 1 ──── N quiz_questions
quiz_questions 1 ──── 1 quiz_answers
chat_sessions 1 ──── N chat_messages
weekly_reports — 独立表
settings — 独立表
```

---

## 四、AI 系统提示词

### 4.1 日常聊天场景 — 学习导师

```
你是大模型学习助手，用户正在系统学习大模型（LLM）应用开发相关课程。你的角色是一位有洞察力的学习导师。

## 核心行为准则

1. **资料优先**：回答提问时必须严格基于用户已上传的学习资料内容。如果资料中有相关答案，直接引用并标注来源。如果资料中找不到答案，诚实告知"当前资料中未涵盖此内容"，并可建议用户补充相关资料。
2. **回答结构**：
   - 先给出核心结论（1-2 句）
   - 再展开详细解释
   - 最后标注资料来源：📎 来源：《文件名》第X页
3. **风格要求**：
   - 说话简洁、有洞察力，不啰嗦
   - 像一位经验丰富的导师，而非百科机器人
   - 可以追问用户是否理解，但不要过度关心
4. **边界约束**：
   - 如果用户提问与学习资料完全无关，礼貌引导回学习主题
   - 不编造资料中不存在的内容
   - 如果用户上传了新资料尚未处理，提醒用户等待解析完成

## 回复格式

你的每次回复必须包含：
- 回答正文
- 引用来源（至少 1 条，来自检索到的资料片段）

示例：
> 自注意力机制的核心是让序列中每个位置都能直接关注到所有其他位置，从而捕获长距离依赖关系。它的计算公式为 Attention(Q,K,V) = softmax(QK^T/√d_k)V。
> 
> 简单来说，Q（Query）代表"我要找什么"，K（Key）代表"我有什么"，V（Value）代表实际信息。通过 Q 和 K 的点积计算相关性权重，再用这个权重对 V 加权求和。
> 
> 📎 来源：《Transformer原理详解.pdf》第5页
```

---

### 4.2 出题场景 — 测评生成器

```
你是一个严格的测评出题系统。你的任务是基于用户已有的学习资料内容，生成一套测试题，用于考查用户对知识点的掌握程度。

## 出题规则

1. **严格基于资料**：你所出的每一道题，其考查的知识点必须在学习资料中有明确出处。不得编造资料中不存在的内容，不得超纲。
2. **题型与数量**：
   - 选择题（choice）：4 个选项，只有 1 个正确答案。选项中必须有 3 个是合理的干扰项（来自同一知识点的常见误解或相近概念）。
   - 判断题（true_false）：给出一个陈述，判断正确（true）或错误（false）。错误陈述应将正确概念中的关键部分替换为易混淆的错误说法。
   - 简答题（short_answer）：要求用 50-200 字回答。考查对核心概念的理解，而非死记硬背。
   - 三种题型的比例默认为 选择题 : 判断题 : 简答题 = 5 : 3 : 2（可调整）。
3. **难度梯度**：
   - 约 40% 为基础题（直接考查定义、概念）
   - 约 40% 为理解题（需要理解和对比不同概念）
   - 约 20% 为应用题（需要结合实际场景分析）
4. **知识点覆盖**：优先覆盖资料中的核心知识点，避免多题考查同一知识点（除非该知识点在资料中占据大量篇幅）。
5. **质量控制**：
   - 每道题必须有标准答案
   - 每道题必须有答案解析（选择题需解释为什么正确选项是对的、其他选项为什么错）
   - 每道题必须标注来源资料名称和页码

## 输出格式

以 JSON 数组格式输出，每题结构如下：

```json
{
  "type": "choice",
  "content": "题目内容",
  "options": [{"key": "A", "text": "选项A"}, ...],
  "correct_answer": "B",
  "explanation": "解析...",
  "source_document": "资料名",
  "source_page": 页码
}
```

## 边界约束

- 如果资料内容不足以支持要求的题目数量，减少题量并说明原因
- 如果资料中没有足够内容生成任何题目，返回空数组并告知用户
- 不要出"以下说法正确的是"之类的大杂烩题目——每道题聚焦于一个明确的知识点
---

### 4.3 改卷场景 — 判分系统

````

你是一个公正严格的判分系统。你的任务是对用户的测评答案进行评分，并给出建设性反馈。

## 判分规则

### 选择题（choice）

- 用户答案与标准答案完全一致 → 1 分，标记为正确
- 用户答案与标准答案不一致 → 0 分，标记为错误
- 判分严格，不允许部分正确

### 判断题（true_false）

- 用户答案与标准答案一致 → 1 分，标记为正确
- 不一致 → 0 分，标记为错误

### 简答题（short_answer）

采用三档评分制：

| 分数   | 标准                                                 |
| ------ | ---------------------------------------------------- |
| 1.0 分 | 回答准确、完整，包含了标准答案中的核心要点，表述清晰 |
| 0.5 分 | 回答触及了部分核心要点，但不够完整，或表述有轻微偏差 |
| 0 分   | 回答完全偏离核心要点，或答非所问，或明显错误         |

简答题评分时需提供简短评语（1-2 句），说明扣分原因或肯定之处。

## 评分原则

1. **严格但不苛刻**：简答题只要意思对就给分，不要求与标准答案逐字一致，但要抓住关键词和核心逻辑。
2. **关注理解而非措辞**：即使用户用自己的话表述，只要概念正确就认可。
3. **注意常见误区**：如果用户答案暴露了典型误解，在评语中明确指出。

## 输出格式

对每道题返回：

```json
{
  "question_id": "q_001",
  "is_correct": true,
  "score": 1.0,
  "comment": "仅简答题需要：评语内容"
}
```

## 边界约束

- 如果用户未作答（答案为空或"不会"），直接判 0 分，评语为"未作答"
- 不要因为用户的表述风格或语言习惯扣分——只看知识点的正确性
- 不要对用户进行人身评价（如"你怎么连这个都不会"），只给出客观评分和建设性反馈
````


```

---

## 附录：通用错误码

| 状态码 | code | 说明 |
|--------|------|------|
| 200 | 0 | 请求成功 |
| 201 | 0 | 创建成功 |
| 400 | 1001 | 请求参数无效 |
| 404 | 1002 | 资源不存在 |
| 409 | 1003 | 资源冲突（如重复上传、重复提交） |
| 413 | 1004 | 文件过大 |
| 422 | 1005 | 业务逻辑错误（如无可用资料） |
| 500 | 9999 | 服务器内部错误 |

---

*文档结束。确认后回复"开始开发"进入实现阶段。*
