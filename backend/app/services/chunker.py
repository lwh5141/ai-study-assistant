"""文本分块服务 — 语义段落分割 + 滑动窗口重叠

策略：
1. 优先按自然段落（\\n\\n）分
2. 段落过长则按句子边界（。！？\\n）再分
3. 句子仍过长则按固定 token 数硬切
4. 相邻块保留 overlap 以保持上下文连续性
"""

import re


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文 1 字 ≈ 1.5 token，英文 1 词 ≈ 1.3 token）"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.3)


def _extract_tail_tokens(text: str, max_tokens: int) -> str:
    """从文本尾部提取约 max_tokens 的文本（用于 overlap 拼接）"""
    if not text or max_tokens <= 0:
        return ''

    tokens = 0.0
    for i in range(len(text) - 1, -1, -1):
        ch = text[i]
        tokens += 1.5 if '\u4e00' <= ch <= '\u9fff' else 0.3
        if tokens >= max_tokens:
            return text[i:]

    return text


def _split_long_paragraph(text: str, max_tokens: int, overlap_tokens: int = 0) -> list[str]:
    """将过长的段落按句子切分，支持 overlap 拼接保持上下文连续性"""
    sentences = re.split(r'(?<=[。！？\n])', text)
    chunks: list[str] = []
    current = ''

    for sent in sentences:
        candidate = current + sent
        if _estimate_tokens(candidate) <= max_tokens:
            current = candidate
        else:
            # 切出当前已累积的 chunk
            if current.strip():
                chunks.append(current.strip())

            # overlap 拼接：从刚切出的 chunk 尾部取 overlap_tokens，
            # 拼到下一块的起始位置
            if overlap_tokens > 0 and current.strip():
                overlap_text = _extract_tail_tokens(current, overlap_tokens)
                current = overlap_text + sent
            else:
                current = sent

            # 如果 overlap + 单句 仍然超长，硬切拆分
            if _estimate_tokens(current) > max_tokens:
                sub_chunks = _hard_split(current, max_tokens, overlap_tokens)
                chunks.extend(sub_chunks)
                current = ''

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _hard_split(text: str, max_tokens: int, overlap_tokens: int = 0) -> list[str]:
    """按字符数硬切（中文约 1 字 = 1.5 token），支持滑动窗口 overlap"""
    char_limit = max(int(max_tokens / 1.5), 50)

    # 守卫：overlap 不应 ≥ chunk_size
    if overlap_tokens >= max_tokens:
        overlap_tokens = 0

    overlap_chars = int(overlap_tokens / 1.5) if overlap_tokens > 0 else 0
    step = char_limit - overlap_chars
    if step <= 0:
        step = char_limit

    result = []
    start = 0
    while start < len(text):
        chunk = text[start:start + char_limit]
        result.append(chunk)
        start += step

    return result


def chunk_document(
    full_text: str,
    pages: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    document_id: str = '',
    document_name: str = '',
) -> list[dict]:
    """
    将文档文本分块，返回 chunk 字典列表。

    每个 chunk:
    {
        'content': str,
        'document_id': str,
        'document_name': str,
        'page_number': int | None,
        'section_title': str | None,
        'chunk_index': int,
        'token_count': int,
    }
    """
    chunks: list[dict] = []
    chunk_index = 0

    if pages:
        # 有页码信息时，逐页分块（跨页不做 overlap）
        for page in pages:
            page_text = page['text']
            if not page_text.strip():
                continue

            page_chunks = _split_long_paragraph(page_text, chunk_size, chunk_overlap)
            for pc in page_chunks:
                token_count = _estimate_tokens(pc)
                chunks.append({
                    'content': pc,
                    'document_id': document_id,
                    'document_name': document_name,
                    'page_number': page.get('page_number'),
                    'section_title': page.get('section_title'),
                    'chunk_index': chunk_index,
                    'token_count': token_count,
                })
                chunk_index += 1
    else:
        # 无页码信息时，整体分块
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        for para in paragraphs:
            para_chunks = _split_long_paragraph(para, chunk_size, chunk_overlap)
            for pc in para_chunks:
                token_count = _estimate_tokens(pc)
                chunks.append({
                    'content': pc,
                    'document_id': document_id,
                    'document_name': document_name,
                    'page_number': None,
                    'section_title': None,
                    'chunk_index': chunk_index,
                    'token_count': token_count,
                })
                chunk_index += 1

    return chunks
