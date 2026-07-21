"""RAG 管道 — 检索 + DeepSeek 生成"""

import json
from typing import Generator
from .hybrid_search import hybrid_search
from .llm import chat_stream

# ---- 提示词（来自需求文档 4.1） ----

TUTOR_SYSTEM_PROMPT = """你是大模型学习助手，用户正在系统学习大模型（LLM）应用开发相关课程。你的角色是一位有洞察力的学习导师。

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
- 引用来源（至少 1 条，来自检索到的资料片段）"""


def build_context(chunks: list[dict]) -> str:
    """将检索到的文本块拼接为结构化上下文"""
    if not chunks:
        return '（暂无相关资料）'

    parts = []
    for i, chunk in enumerate(chunks):
        doc_name = chunk.get('document_name', '未知资料')
        page = chunk.get('page', '?')
        parts.append(f"[来源{i+1}] 《{doc_name}》第{page}页:\n{chunk.get('excerpt', '')}")
    return '\n\n---\n\n'.join(parts)


def rag_query(
    question: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
    chat_history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """RAG 查询流式输出"""
    # 1. 检索（混合检索：向量 + BM25 关键词）
    chunks = hybrid_search(question, top_k=top_k, document_ids=document_ids)
    context = build_context(chunks)

    # 2. 构建消息
    messages = [{'role': 'system', 'content': TUTOR_SYSTEM_PROMPT}]

    # 插入历史（最近 10 轮）
    if chat_history:
        for msg in chat_history[-20:]:
            messages.append({
                'role': msg['role'],
                'content': msg['content'],
            })

    messages.append({
        'role': 'user',
        'content': f'【参考资料】\n{context}\n\n【用户问题】\n{question}',
    })

    # 3. 流式生成
    yield from chat_stream(messages, temperature=0.7)

    # 4. 末尾附带 sources（通过特殊 token 标记）
    yield '\n<!--SOURCES:' + json.dumps(chunks, ensure_ascii=False) + '-->'
