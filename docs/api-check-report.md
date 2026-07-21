# 前后端接口一致性检查报告

> 日期：2026-07-20 | 检查范围：全部 20 个 API 端点

---

## 一、接口覆盖检查 ✅

21 个前端函数 → 21 个后端路由，**全部匹配，无缺失接口**。

后端有 3 个额外端点前端未使用（reparse/download/weak-points），非缺陷，后续可接入。

---

## 二、数据格式兼容检查

### 已修复的问题

| # | 问题 | 文件 | 修复内容 |
|---|------|------|----------|
| P0-1 | `QuizQuestion.to_dict()` options 返回 JSON 字符串 | `models.py:211` | 添加 `json.loads()` 反序列化 |
| P0-2 | SSE onDone 回调将流式累积 content 覆盖为 undefined | `StudyPage.tsx:85` | 移除 `content: result.content` 覆盖逻辑 |
| P1-1 | 非流式 chat 响应缺少 `created_at` | `chat.py:148` | 添加 `created_at` 字段 |
| P1-2 | `ChatMessage.to_dict()` sources 返回原始字符串 | `models.py:141` | 添加 `json.loads()` 反序列化 |
| P1-3 | `QuizResultDetail.source_page` 始终为 None | `models.py` + `quiz.py` | 新增 `source_page` 列，出题时存储，结果中返回 |
| P1-4 | `WrongQuestion` 缺少 `created_at` | `quiz.py:344` | 添加 `created_at` 字段 |

### 无需修复的差异（设计如此）

| 字段 | 说明 |
|------|------|
| `QuizHistoryItem accuracy` 可为 null | 已提交测评才有此值，前端类型 `number?` 兼容 |
| `SendMessageResponse.role` 在 SSE done 中缺失 | 前端 onDone 不需要此字段 |
| Settings 路由路径 | 确认 `report_bp` 注册时 url_prefix 为 `/api/v1`（无 `/report`），路径正确 |

---

## 三、Quiz Options 数据类型转换 ✅ 已修复

**问题：** `QuizQuestion.to_dict()` 返回 options 为 JSON 字符串，前端 `question.options.map()` → TypeError

**修复：** `models.py` `to_dict()` 中添加 `json.loads(self.options)` 反序列化，确保返回 `QuizOption[]` 对象数组。

---

## 四、判断题 Options 格式 ✅ 一致

前端判断题渲染**硬编码** `true`/`false` 两个按钮，不依赖 `question.options` 字段。后端 `correct_answer` 存储 `"true"`/`"false"` 字符串。前后端完全一致，无需 `{"A":"正确","B":"错误"}` 格式。

---

## 五、验证结果

| 检查项 | 结果 |
|--------|------|
| `tsc -b` 前端编译 | ✅ 零错误 |
| Flask 后端重启 | ✅ 正常 |
| 21 个 API 端点可调用 | ✅ |
| options JSON 反序列化 | ✅ |
| SSE content 不丢失 | ✅ |
| source_page 存储与返回 | ✅ |
| created_at 补全 | ✅ |
