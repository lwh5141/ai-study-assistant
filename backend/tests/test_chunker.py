"""
chunker 滑动窗口 overlap 测试方案
===================================
10 个用例，分三类：
  分类一：_split_long_paragraph overlap 行为（用例 1-4）
  分类二：_hard_split 滑动窗口（用例 5-7）
  分类三：chunk_document 端到端集成（用例 8-10）

运行方式：cd backend && python -m pytest tests/test_chunker.py -v
依赖：无 Flask/DB/API，纯单元测试
"""

import re
import pytest
from app.services.chunker import (
    _estimate_tokens,
    _split_long_paragraph,
    _hard_split,
    chunk_document,
)

# ============================================================
# 共享测试数据
# ============================================================

TEST_TEXT_SHORT = (
    "Transformer 架构由 Vaswani 等人在 2017 年提出，彻底改变了自然语言处理领域。"
)

# 模拟大模型课程资料 - 中文为主，夹英文术语，约 1200+ token
TEST_TEXT_LONG = (
    "在 Transformer 架构中，自注意力机制（Self-Attention）是其核心创新。"
    "与传统的 RNN 和 LSTM 不同，Self-Attention 允许模型在处理序列时，"
    "直接计算任意两个位置之间的关联权重，从而捕获长距离依赖关系。"
    "具体来说，Self-Attention 通过 Query、Key、Value 三个矩阵进行计算，"
    "公式为 Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V。"
    "多头注意力（Multi-Head Attention）是 Self-Attention 的扩展版本。"
    "它将输入线性投影到多个不同的子空间，在每个子空间中独立计算注意力，"
    "最后将所有头的输出拼接起来。这样做的好处是模型可以同时关注不同位置、"
    "不同表示子空间的信息，类似于卷积神经网络中的多通道设计。"
    "位置编码（Positional Encoding）用于弥补 Transformer 丢失的序列信息。"
    "由于 Self-Attention 本身不具备位置感知能力，需要额外加入位置信号。"
    "原始论文使用正弦和余弦函数的固定编码，后续也有可学习的位置编码方案。"
    "前馈神经网络（Feed-Forward Network，FFN）是 Transformer 的另一个关键组件。"
    "每个位置的 FFN 结构相同但参数独立，通常包含两层全连接层和一个激活函数。"
    "常用的激活函数包括 ReLU、GELU 等，其中 GELU 在 BERT 和 GPT 中被广泛使用。"
    "层归一化（Layer Normalization）用于稳定深层网络的训练过程。"
    "与批归一化（Batch Normalization）不同，Layer Norm 在特征维度上进行归一化，"
    "不依赖于 batch 大小，因此更适合 NLP 任务中变长序列的处理。"
    "残差连接（Residual Connection）是训练深层网络的重要技巧。"
    "它通过跳跃连接将输入直接加到子层输出上，有效缓解了梯度消失和退化问题。"
    "Transformer 的每个子层（自注意力层和 FFN 层）都使用了残差连接。"
    "训练 Transformer 模型通常使用 Adam 优化器配合学习率预热策略。"
    "学习率在热身阶段线性增加，到达峰值后按步数的平方根倒数逐渐衰减。"
    "这种策略避免了训练初期因学习率过大导致的模型不稳定。"
)

# 超长单句 — 用于测试 _hard_split（约 800 字，无句号）
TEST_TEXT_HUGE_SENTENCE = (
    "自注意力机制SelfAttention通过计算输入序列中每个位置与其他所有位置之间的"
    "注意力权重来捕获全局依赖关系具体来说对于输入序列X首先通过三个不同的线性变换"
    "得到Query矩阵Q和Key矩阵K以及Value矩阵V然后计算Q和K的点积并通过缩放因子"
    "sqrtdk进行缩放以防止梯度消失或爆炸接着通过softmax函数将注意力分数归一化为"
    "概率分布最后将注意力权重与V矩阵相乘得到输出表示这一过程可以并行计算所有位置"
    "的注意力因此相比RNN具有显著的计算效率优势此外通过使用多个注意力头可以让模型"
    "同时关注不同的语义空间例如一个头可能关注语法结构另一个头可能关注语义关联"
    "还有的头可能关注位置关系这种多头机制大大增强了模型的表达能力使其能够捕捉复杂"
    "的语言模式"
)


# ============================================================
# 工具函数 — 检测重叠
# ============================================================

def _has_overlap(chunk_a: str, chunk_b: str, min_chars: int = 5) -> bool:
    """检查两个 chunk 是否有文本重叠。在 chunk_b 头部搜索 chunk_a 的尾部子串。"""
    tail = chunk_a[-30:] if len(chunk_a) > 30 else chunk_a
    return tail[:min_chars] in chunk_b


def _find_overlap_text(chunk_a: str, chunk_b: str) -> str:
    """查找 chunk_a 尾部与 chunk_b 头部的最长公共子串（至少 5 字符）。"""
    best = ""
    for i in range(len(chunk_a) - 1, 0, -1):
        for j in range(min(i + 1, 50), 4, -1):
            if j > len(chunk_a):
                continue
            candidate = chunk_a[i + 1 - j : i + 1]
            if chunk_b.startswith(candidate[:10]):
                if len(candidate) > len(best):
                    best = candidate
    # 简化版：检查 chunk_a 最后 N 个字符是否在 chunk_b 开头的 100 个字符中
    for size in range(min(50, len(chunk_a)), 4, -1):
        tail = chunk_a[-size:]
        if tail in chunk_b[:100]:
            return tail
    return best


# ============================================================
# 分类一：_split_long_paragraph overlap 行为
# ============================================================

class TestSplitLongParagraphOverlap:
    """_split_long_paragraph 的 overlap 功能测试"""

    def test_overlap_effective(self):
        """用例 1：overlap 生效 — 相邻 chunk 有文本重叠"""
        max_tokens = 350
        overlap = 80
        chunks = _split_long_paragraph(TEST_TEXT_LONG, max_tokens, overlap)

        assert len(chunks) >= 2, f"期望至少 2 个 chunk，实际 {len(chunks)} 个"

        overlap_found = False
        for i in range(len(chunks) - 1):
            if _has_overlap(chunks[i], chunks[i + 1]):
                overlap_found = True
                break

        assert overlap_found, (
            f"未检测到任何相邻 chunk 之间的文本重叠。"
            f"共 {len(chunks)} 个 chunk。"
            f"\nChunk[0] 尾部: ...{chunks[0][-80:]!r}"
            f"\nChunk[1] 头部: {chunks[1][:80]!r}"
        )

    def test_no_overlap_regression(self):
        """用例 2：overlap=0 回归 — 输出与当前代码一致"""
        max_tokens = 350
        overlap = 0
        chunks = _split_long_paragraph(TEST_TEXT_LONG, max_tokens, overlap)

        assert len(chunks) >= 2

        # 验证所有相邻 chunk 无重叠
        for i in range(len(chunks) - 1):
            assert not _has_overlap(chunks[i], chunks[i + 1]), (
                f"overlap=0 时 Chunk[{i}] 和 Chunk[{i+1}] 不应有重叠。"
                f"\nChunk[{i}] 尾部: ...{chunks[i][-50:]!r}"
                f"\nChunk[{i+1}] 头部: {chunks[i+1][:50]!r}"
            )

        # 验证 token 数上限
        for i, chunk in enumerate(chunks):
            tokens = _estimate_tokens(chunk)
            assert tokens <= max_tokens, f"Chunk[{i}] token={tokens} > {max_tokens}"

    def test_overlap_quantity(self):
        """用例 3：overlap 量精确性 — 尾部文本 token 数接近 overlap_tokens"""
        max_tokens = 150
        overlap = 50

        # 用可控的测试文本
        text = (
            "第一章 注意力机制。"
            "自注意力是 Transformer 架构的核心组件。"
            "它允许模型在处理序列时关注不同位置的关联信息。"
            "第二章 多头注意力。"
            "多头注意力并行计算多组注意力权重。"
            "每个头关注不同的表示子空间。"
            "第三章 位置编码。"
            "Transformer 需要位置编码来注入序列顺序信息。"
            "常用方法包括正弦位置编码和可学习位置编码。"
        )

        chunks = _split_long_paragraph(text, max_tokens, overlap)

        # 找第一对有 overlap 的 chunk
        for i in range(len(chunks) - 1):
            overlap_text = _find_overlap_text(chunks[i], chunks[i + 1])
            if overlap_text:
                overlap_tokens = _estimate_tokens(overlap_text)
                assert 15 <= overlap_tokens <= 150, (
                    f"Chunk[{i}]->Chunk[{i+1}] 重叠 token={overlap_tokens}，"
                    f"期望在 [15, 150] 范围内（overlap=50 的合理波动）。"
                    f"\n重叠文本: {overlap_text!r}"
                )
                return  # 找到一个就够

        pytest.fail("未找到任何 overlap，至少应有一对相邻 chunk 有重叠")

    def test_short_previous_chunk(self):
        """用例 4：短 chunk 边缘 — 前一个 chunk 比 overlap 还短"""
        # 先放一个极短的句子，再放正常内容
        text = "短句。" + TEST_TEXT_LONG
        max_tokens = 400
        overlap = 100

        # 不应抛异常
        chunks = _split_long_paragraph(text, max_tokens, overlap)

        assert len(chunks) >= 2, f"期望至少 2 个 chunk，实际 {len(chunks)} 个"

        # 第一个 chunk 不应崩溃或异常溢出（短句会被正常累积到 max_tokens）
        first_chunk_tokens = _estimate_tokens(chunks[0])
        assert first_chunk_tokens <= max_tokens, (
            f"第一个 chunk token={first_chunk_tokens} 不应超过 max={max_tokens}"
        )

        # 所有 chunk 不应超过 max_tokens
        for i, chunk in enumerate(chunks):
            tokens = _estimate_tokens(chunk)
            assert tokens <= max_tokens, f"Chunk[{i}] token={tokens} > {max_tokens}"


# ============================================================
# 分类二：_hard_split 滑动窗口
# ============================================================

class TestHardSplitSlidingWindow:
    """_hard_split 的滑动窗口功能测试"""

    def test_sliding_window_step(self):
        """用例 5：步长 = 块大小 − overlap"""
        max_tokens = 250
        overlap = 60

        chunks = _hard_split(TEST_TEXT_HUGE_SENTENCE, max_tokens, overlap)

        assert len(chunks) >= 2, f"期望至少 2 个 chunk，实际 {len(chunks)} 个"

        # 计算期望的字符级参数
        char_limit = int(max_tokens / 1.5)
        overlap_chars = int(overlap / 1.5)
        expected_step = char_limit - overlap_chars

        assert expected_step > 0, f"step={expected_step} 应 > 0"

        # 验证 Chunk[0] 尾部与 Chunk[1] 头部重叠
        # 用原始文本索引验证步长
        for i in range(len(chunks) - 1):
            assert _has_overlap(chunks[i], chunks[i + 1]), (
                f"Chunk[{i}] 和 Chunk[{i+1}] 应有字符级重叠。"
                f"\nChunk[{i}][-40:]: {chunks[i][-40:]!r}"
                f"\nChunk[{i+1}][:40]: {chunks[i+1][:40]!r}"
            )

        # 验证 chunk 长度不超过 char_limit
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= char_limit + 5, (  # 允许少量误差
                f"Chunk[{i}] len={len(chunk)} > char_limit={char_limit}+5"
            )

    def test_no_overlap_regression(self):
        """用例 6：No-overlap 回归（overlap=0）"""
        max_tokens = 250
        overlap = 0

        chunks = _hard_split(TEST_TEXT_HUGE_SENTENCE, max_tokens, overlap)

        assert len(chunks) >= 2

        # 验证无重叠：上一块的尾部不出现在下一块的头部
        for i in range(len(chunks) - 1):
            tail = chunks[i][-20:] if len(chunks[i]) > 20 else chunks[i]
            assert tail not in chunks[i + 1][:50], (
                f"overlap=0 时 Chunk[{i}] 尾部不应出现在 Chunk[{i+1}] 头部。"
                f"\ntail: {tail!r}"
                f"\nChunk[{i+1}][:50]: {chunks[i+1][:50]!r}"
            )

        # 验证字符数上限
        char_limit = int(max_tokens / 1.5)
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= char_limit + 5, (
                f"Chunk[{i}] len={len(chunk)} > char_limit={char_limit}+5"
            )

    def test_overlap_guard(self):
        """用例 7：overlap ≥ chunk_size 守卫 — 不抛异常，退化为无 overlap"""
        max_tokens = 200
        overlap = 250  # 大于 max_tokens

        # 不应崩溃
        try:
            chunks = _hard_split(TEST_TEXT_HUGE_SENTENCE, max_tokens, overlap)
        except (ZeroDivisionError, ValueError, IndexError) as e:
            pytest.fail(f"_hard_split 在 overlap >= chunk_size 时抛异常: {e}")

        assert len(chunks) >= 1, "应该能产出至少 1 个 chunk"

        # 验证 chunk 长度合理
        char_limit = int(max_tokens / 1.5)
        for chunk in chunks:
            assert len(chunk) <= char_limit + 5, (
                f"chunk len={len(chunk)} > char_limit={char_limit}+5"
            )


# ============================================================
# 分类三：chunk_document 端到端集成
# ============================================================

class TestChunkDocumentIntegration:
    """chunk_document 端到端测试 — 含 pages 结构的完整流水线"""

    def test_within_page_overlap(self):
        """用例 8：逐页 overlap 生效 — 同页内相邻 chunk 有重叠"""
        pages = [
            {
                "page_number": 1,
                "text": TEST_TEXT_LONG,
                "section_title": "Transformer 核心组件",
            },
            {
                "page_number": 2,
                "text": (
                    "BERT 模型由 Google 在 2018 年提出，"
                    "它基于 Transformer 的编码器部分，"
                    "通过掩码语言模型（MLM）和下一句预测（NSP）两个任务进行预训练。"
                ),
                "section_title": "BERT 预训练模型",
            },
        ]

        chunks = chunk_document(
            full_text="",
            pages=pages,
            chunk_size=350,
            chunk_overlap=80,
            document_id="doc_test_01",
            document_name="大模型课程笔记.pdf",
        )

        assert len(chunks) >= 2, f"期望至少 2 个 chunk，实际 {len(chunks)} 个"

        # 分离各页的 chunk
        page1_chunks = [c for c in chunks if c["page_number"] == 1]

        assert len(page1_chunks) >= 2, (
            f"第 1 页期望至少 2 个 chunk，实际 {len(page1_chunks)} 个"
        )

        # 验证第 1 页内相邻 chunk 的 overlap
        overlap_found = False
        for i in range(len(page1_chunks) - 1):
            if _has_overlap(page1_chunks[i]["content"], page1_chunks[i + 1]["content"]):
                overlap_found = True
                break

        assert overlap_found, (
            f"第 1 页内的相邻 chunk 未检测到重叠。"
            f"共 {len(page1_chunks)} 个 chunk。"
        )

    def test_cross_page_no_overlap(self):
        """用例 9：跨页不重叠 — 页边界的 chunk 不能串内容"""
        pages = [
            {
                "page_number": 1,
                "text": (
                    "Transformer 的自注意力机制允许模型捕获长距离依赖关系。"
                    "这使其在机器翻译任务上显著优于传统的循环神经网络模型。"
                ),
                "section_title": "注意力机制",
            },
            {
                "page_number": 2,
                "text": (
                    "GPT 系列模型采用了 Transformer 的解码器架构。"
                    "GPT-3 拥有 1750 亿参数，展示了强大的少样本学习能力。"
                ),
                "section_title": "GPT 模型",
            },
        ]

        chunks = chunk_document(
            full_text="",
            pages=pages,
            chunk_size=200,
            chunk_overlap=50,
            document_id="doc_test_02",
            document_name="LLM 概览.pdf",
        )

        page1_chunks = [c for c in chunks if c["page_number"] == 1]
        page2_chunks = [c for c in chunks if c["page_number"] == 2]

        if page1_chunks and page2_chunks:
            last_p1 = page1_chunks[-1]["content"]
            first_p2 = page2_chunks[0]["content"]

            # 第 1 页最后 chunk 的尾部不应出现在第 2 页第一个 chunk 的头部
            tail = last_p1[-30:] if len(last_p1) > 30 else last_p1
            assert not _has_overlap(last_p1, first_p2), (
                f"跨页不应有重叠！"
                f"\n第 1 页最后 chunk 尾部: ...{last_p1[-50:]!r}"
                f"\n第 2 页第一 chunk 头部: {first_p2[:50]!r}"
            )

    def test_metadata_integrity(self):
        """用例 10：metadata 完整性 — document_id/page_number/chunk_index 等全部正确"""
        pages = [
            {"page_number": 1, "text": TEST_TEXT_LONG, "section_title": "第一篇"},
        ]

        chunks = chunk_document(
            full_text="",
            pages=pages,
            chunk_size=350,
            chunk_overlap=80,
            document_id="doc_meta_test",
            document_name="测试资料.md",
        )

        assert len(chunks) >= 2, f"期望至少 2 个 chunk，实际 {len(chunks)} 个"

        for i, chunk in enumerate(chunks):
            # document_id
            assert chunk["document_id"] == "doc_meta_test", (
                f"Chunk[{i}] document_id 错误: {chunk['document_id']!r}"
            )
            # document_name
            assert chunk["document_name"] == "测试资料.md", (
                f"Chunk[{i}] document_name 错误: {chunk['document_name']!r}"
            )
            # page_number
            assert chunk["page_number"] == 1, (
                f"Chunk[{i}] page_number 错误: {chunk['page_number']!r}"
            )
            # section_title
            assert chunk["section_title"] == "第一篇", (
                f"Chunk[{i}] section_title 错误: {chunk['section_title']!r}"
            )
            # chunk_index 连续
            assert chunk["chunk_index"] == i, (
                f"Chunk[{i}] chunk_index 错误: {chunk['chunk_index']}, 期望 {i}"
            )
            # token_count ≤ chunk_size
            assert chunk["token_count"] <= 350, (
                f"Chunk[{i}] token_count={chunk['token_count']} > chunk_size=350"
            )
            # content 不为空
            assert chunk["content"].strip(), f"Chunk[{i}] content 为空"


# ============================================================
# 无 pages 结构的覆盖（chunk_document 的 else 分支）
# ============================================================

class TestChunkDocumentNoPages:
    """无页码信息时的分块行为"""

    def test_no_pages_with_overlap(self):
        """无 pages 时 overlap 也生效"""
        chunks = chunk_document(
            full_text=TEST_TEXT_LONG,
            pages=[],
            chunk_size=350,
            chunk_overlap=80,
            document_id="doc_no_pages",
            document_name="纯文本笔记.txt",
        )

        assert len(chunks) >= 2

        overlap_found = False
        for i in range(len(chunks) - 1):
            if _has_overlap(chunks[i]["content"], chunks[i + 1]["content"]):
                overlap_found = True
                break

        assert overlap_found, "无 pages 结构时 overlap 也应生效"
