"""LLM 服务 — DeepSeek API（OpenAI 兼容）+ 最多 3 次重试 + Markdown 剥离"""

import re
import json
import time
from typing import Generator, Optional
from openai import OpenAI
from flask import current_app


# ---- 客户端（懒加载） ----

_llm_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        api_key = current_app.config.get('LLM_API_KEY', '')
        base_url = current_app.config.get('LLM_API_URL', '')
        if not api_key:
            raise RuntimeError('LLM_API_KEY 未配置')
        _llm_client = OpenAI(api_key=api_key, base_url=base_url)
    return _llm_client


def reset_client() -> None:
    """重置 LLM 客户端缓存（配置变更后调用）"""
    global _llm_client
    _llm_client = None


# ---- 重试装饰器 ----

def _retry(func, *args, max_retries: int = 3, **kwargs):
    """带重试的调用"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 8)  # 1s, 2s, 4s max 8s
                time.sleep(wait)
    raise last_error  # type: ignore


# ---- Markdown 代码块剥离 ----

def strip_markdown_code(text: str) -> str:
    """剥离 AI 返回的 ```json ... ``` 包裹，提取纯 JSON"""
    text = text.strip()
    # 匹配 ```json / ``` 包裹
    pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 可能只有开头没有结尾
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


# ---- 核心调用 ----

def chat_complete(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """非流式对话，自动重试"""
    client = _get_client()
    model = current_app.config.get('LLM_MODEL_NAME', 'deepseek-chat')
    max_retries = current_app.config.get('LLM_MAX_RETRIES', 3)

    def _call():
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ''

    return _retry(_call, max_retries=max_retries)


def chat_complete_json(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> dict | list:
    """非流式对话，自动剥离 markdown 后解析 JSON，失败则重试"""
    raw = chat_complete(messages, temperature=temperature, max_tokens=max_tokens)
    stripped = strip_markdown_code(raw)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # 再试一次：让 AI 修复 JSON
        messages.append({'role': 'assistant', 'content': raw})
        messages.append({
            'role': 'user',
            'content': '你返回的内容不是有效的 JSON，请重新以纯 JSON 格式输出，不要用 markdown 包裹。',
        })
        raw2 = chat_complete(messages, temperature=0, max_tokens=max_tokens)
        stripped2 = strip_markdown_code(raw2)
        return json.loads(stripped2)


def chat_stream(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Generator[str, None, None]:
    """流式对话生成器，自动重试"""
    client = _get_client()
    model = current_app.config.get('LLM_MODEL_NAME', 'deepseek-chat')
    max_retries = current_app.config.get('LLM_MAX_RETRIES', 3)
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
            return  # 成功，退出
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 8)
                time.sleep(wait)

    raise last_error  # type: ignore
