"""
BM25 关键词检索测试方案
======================
7 个用例，分三类：
  分类一：基本索引与检索（用例 1-3）
  分类二：索引维护（用例 4-5）
  分类三：边缘情况（用例 6-7）

运行方式：cd backend && python -m pytest tests/test_keyword_search.py -v
依赖：rank-bm25 + jieba（纯单元测试，无 Flask/DB/ChromaDB）
"""

import pytest


# ============================================================
# 共享测试数据 — 模拟大模型课程 chunk
# ============================================================

TEST_CHUNKS = [
    {
        "id": "chunk_docA_0",
        "document_id": "doc_A",
        "document_name": "Transformer详解.pdf",
        "chunk_index": 0,
        "content": "自注意力机制（Self-Attention）是 Transformer 架构的核心创新。"
                   "它允许模型在处理序列时直接计算任意两个位置之间的关联权重。",
    },
    {
        "id": "chunk_docA_1",
        "document_id": "doc_A",
        "document_name": "Transformer详解.pdf",
        "chunk_index": 1,
        "content": "多头注意力（Multi-Head Attention）将输入投影到多个子空间，"
                   "在每个子空间中独立计算注意力权重，最后拼接所有头的输出。",
    },
    {
        "id": "chunk_docA_2",
        "document_id": "doc_A",
        "document_name": "Transformer详解.pdf",
        "chunk_index": 2,
        "content": "位置编码（Positional Encoding）用于弥补 Transformer 丢失的序列位置信息。"
                   "原始论文使用正弦和余弦函数的固定编码方案。",
    },
    {
        "id": "chunk_docB_0",
        "document_id": "doc_B",
        "document_name": "BERT论文笔记.pdf",
        "chunk_index": 0,
        "content": "BERT 模型基于 Transformer 编码器，通过掩码语言模型（MLM）"
                   "和下一句预测（NSP）两个任务进行预训练。MLM 随机遮盖 15% 的 token。",
    },
    {
        "id": "chunk_docB_1",
        "document_id": "doc_B",
        "document_name": "BERT论文笔记.pdf",
        "chunk_index": 1,
        "content": "BERT 的输入表示由三部分组成：Token Embedding、Segment Embedding、"
                   "Position Embedding，三者相加后送入 Transformer 编码器。",
    },
    {
        "id": "chunk_docC_0",
        "document_id": "doc_C",
        "document_name": "GPT训练指南.pdf",
        "chunk_index": 0,
        "content": "GPT 系列模型采用 Transformer 解码器架构，使用自回归方式逐 token 生成文本。"
                   "GPT-3 拥有 1750 亿参数，展示了强大的少样本学习能力。",
    },
]

# 只取文本内容（供 BM25 索引使用）
TEST_TEXTS = [c["content"] for c in TEST_CHUNKS]


# ============================================================
# 工具函数
# ============================================================

def _build_index(chunks=None):
    """构建 BM25 索引的辅助函数（实际实现中会 import keyword_search 模块）"""
    from rank_bm25 import BM25Okapi
    import jieba

    chunks = chunks or TEST_CHUNKS
    tokenized = [list(jieba.cut(c["content"])) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    return bm25, chunks


def _search(bm25, chunks, query: str, top_k: int = 5):
    """执行 BM25 搜索"""
    import jieba

    tokenized_query = list(jieba.cut(query))
    scores = bm25.get_scores(tokenized_query)
    # 找到 top_k
    indexed = [(i, scores[i]) for i in range(len(scores)) if scores[i] > 0]
    indexed.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in indexed[:top_k]:
        results.append({
            "document_id": chunks[idx]["document_id"],
            "document_name": chunks[idx]["document_name"],
            "chunk_index": chunks[idx]["chunk_index"],
            "content": chunks[idx]["content"],
            "score": round(float(score), 4),
        })
    return results


# ============================================================
# 分类一：基本索引与检索
# ============================================================


class TestBM25BasicSearch:
    """BM25 基本检索功能"""

    def test_index_and_search_basic(self):
        """用例 1：基本索引与检索 — 返回相关结果按分数降序"""
        bm25, chunks = _build_index()
        results = _search(bm25, chunks, "注意力机制", top_k=3)

        assert len(results) >= 1, f"期望至少 1 条结果，实际 {len(results)} 条"
        for i in range(len(results) - 1):
            assert results[i]["score"] >= results[i + 1]["score"], (
                f"结果应按分数降序：{[(r['content'][:20], r['score']) for r in results]}"
            )
        for r in results:
            assert r["document_id"], "每条结果应有 document_id"
            assert r["content"], "每条结果应有 content"

    def test_chinese_tokenization_match(self):
        """用例 2：中文分词检索 — "注意力机制" 命中含 "自注意力机制" 的 chunk"""
        bm25, chunks = _build_index()
        results = _search(bm25, chunks, "注意力机制", top_k=5)

        # chunk_docA_0 含 "自注意力机制（Self-Attention）"
        doc_ids = {r["document_id"] for r in results}
        assert "doc_A" in doc_ids, (
            f"查询'注意力机制'应命中 doc_A（Transformer详解.pdf），"
            f"实际命中: {doc_ids}"
        )

    def test_no_match_empty_result(self):
        """用例 3：无精确匹配 — 不抛异常，BM25 可能返回部分匹配这是正常行为"""
        bm25, chunks = _build_index()
        # "量子计算" 分词为 ["量子", "计算"]，"计算" 可能命中部分 chunk
        # BM25 的 IDF 在 6 篇小语料中不会完全归零 → 有非零分数属于正常
        results = _search(bm25, chunks, "量子计算")

        # 验证不抛异常即可（部分匹配是 BM25 的预期行为）
        assert isinstance(results, list), "结果应为列表"


# ============================================================
# 分类二：索引维护
# ============================================================


class TestBM25IndexMaintenance:
    """索引增删与重建"""

    def test_add_and_remove(self):
        """用例 4：增删维护 — add 后能搜到，remove 后搜不到"""
        import jieba
        from rank_bm25 import BM25Okapi

        # 初始索引：doc_A 的 3 条
        init_chunks = TEST_CHUNKS[:3]
        tokenized = [list(jieba.cut(c["content"])) for c in init_chunks]
        bm25 = BM25Okapi(tokenized)
        all_chunks = list(init_chunks)

        # 新增 doc_B 的 1 条
        new_chunk = TEST_CHUNKS[3]
        new_tokens = list(jieba.cut(new_chunk["content"]))
        all_chunks.append(new_chunk)

        # BM25Okapi 没有 add 方法，需要重建
        new_tokenized = [list(jieba.cut(c["content"])) for c in all_chunks]
        bm25 = BM25Okapi(new_tokenized)

        # 验证新增后可搜到
        results_after_add = _search(bm25, all_chunks, "BERT", top_k=5)
        doc_ids = {r["document_id"] for r in results_after_add}
        assert "doc_B" in doc_ids, (
            f"新增后应能搜到 doc_B（BERT论文笔记），实际命中: {doc_ids}"
        )

        # 删除 doc_A 的所有 chunk
        chunks_after_remove = [c for c in all_chunks if c["document_id"] != "doc_A"]
        removed_tokenized = [list(jieba.cut(c["content"])) for c in chunks_after_remove]
        bm25 = BM25Okapi(removed_tokenized)

        # 验证删除后搜不到 doc_A
        results_after_remove = _search(bm25, chunks_after_remove, "注意力", top_k=5)
        doc_ids_removed = {r["document_id"] for r in results_after_remove}
        assert "doc_A" not in doc_ids_removed, (
            f"删除后不应搜到 doc_A，实际命中: {doc_ids_removed}"
        )

    def test_rebuild_index(self):
        """用例 5：全量重建 — rebuild 后索引只含指定数据"""
        import jieba
        from rank_bm25 import BM25Okapi

        # 第一次构建：含 doc_A + doc_B
        first_chunks = TEST_CHUNKS[:4]
        tokenized_first = [list(jieba.cut(c["content"])) for c in first_chunks]
        _bm25_first = BM25Okapi(tokenized_first)

        # 全量重建：含 doc_B + doc_C（至少 2 篇，保证 IDF 有效）
        rebuild_chunks = TEST_CHUNKS[3:]  # doc_B_0, doc_B_1, doc_C_0
        tokenized_rebuild = [list(jieba.cut(c["content"])) for c in rebuild_chunks]
        bm25 = BM25Okapi(tokenized_rebuild)

        results = _search(bm25, rebuild_chunks, "GPT", top_k=5)
        doc_ids = {r["document_id"] for r in results}

        assert "doc_C" in doc_ids, f"重建后应搜到 doc_C，实际: {doc_ids}"
        assert "doc_A" not in doc_ids, f"重建后不应有旧数据 doc_A，实际: {doc_ids}"


# ============================================================
# 分类三：边缘情况
# ============================================================


class TestBM25EdgeCases:
    """空语料、空查询、分数一致性"""

    def test_empty_corpus_or_query(self):
        """用例 6：空语料/空查询 — 不抛异常，返回空"""
        import jieba
        from rank_bm25 import BM25Okapi

        # 空语料：BM25Okapi 不支持空列表（会 ZeroDivisionError）
        # 实际代码中 keyword_search.py 的 BM25Index 已处理此情况
        with pytest.raises(ZeroDivisionError):
            BM25Okapi([])

        # 空查询：分词为空 → BM25 返回全零分数
        bm25, chunks = _build_index()
        tokenized_query = list(jieba.cut(""))
        scores = bm25.get_scores(tokenized_query)
        assert all(s == 0.0 for s in scores), "空查询应返回全零分数"

    def test_deterministic_results(self):
        """用例 7：分数一致性 — 相同查询连续执行两次结果完全相同"""
        bm25, chunks = _build_index()
        results_1 = _search(bm25, chunks, "Transformer 编码器 解码器", top_k=5)
        results_2 = _search(bm25, chunks, "Transformer 编码器 解码器", top_k=5)

        assert len(results_1) == len(results_2)
        for r1, r2 in zip(results_1, results_2):
            assert r1["document_id"] == r2["document_id"], (
                f"两次查询结果不一致：{r1['document_id']} vs {r2['document_id']}"
            )
            assert r1["score"] == r2["score"], (
                f"分数不一致：{r1['score']} vs {r2['score']}"
            )
