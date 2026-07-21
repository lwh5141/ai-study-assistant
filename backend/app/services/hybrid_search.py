"""混合检索 — Dense（向量）+ Sparse（BM25）→ RRF 融合

参考资料：混合检索 = lexical + dense 融合召回，
          融合方法使用 RRF（Reciprocal Rank Fusion），无需调权。
"""

import logging
from flask import current_app
from .embedding import search_similar
from .keyword_search import get_bm25_index

logger = logging.getLogger(__name__)


def _chunk_key(item: dict) -> str:
    """chunk 的唯一标识（用于 RRF 去重）"""
    return f"{item.get('document_id', '')}_{item.get('chunk_index', 0)}"


def _normalize_relevance_scores(results: list[dict]) -> list[dict]:
    """将融合后各路的 relevance_score 统一归一化到 0~1（基于排名倒数）。

    Dense 路用余弦相似度（0~1），Sparse 路用 BM25 分数（0~∞），
    两路量纲不同。融合后按排名重新赋值，前端可直接 *100 显示百分比。
    """
    for rank, item in enumerate(results):
        item["relevance_score"] = round(1.0 / (1 + 0.2 * rank), 4)
    return results


def rrf_fuse(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
    top_k: int = 5,
) -> list[dict]:
    """
    RRF 融合两组排序结果。

    公式: score = Σ 1/(k + rank_i)，对所有 retriever 累加。

    参数：
      dense_results:  向量检索结果（已排序）
      sparse_results: BM25 检索结果（已排序）
      k:     RRF 平滑参数（默认 60，标准值）
      top_k: 最终返回数量

    返回：融合排序后的结果列表
    """
    if not dense_results and not sparse_results:
        return []

    if not sparse_results:
        return dense_results[:top_k]
    if not dense_results:
        return sparse_results[:top_k]

    rrf_scores: dict[str, float] = {}
    key_to_item: dict[str, dict] = {}

    # Dense 路
    for rank, item in enumerate(dense_results):
        key = _chunk_key(item)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        key_to_item[key] = item

    # Sparse 路
    for rank, item in enumerate(sparse_results):
        key = _chunk_key(item)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in key_to_item:
            key_to_item[key] = item

    # 按 RRF 分数降序
    sorted_keys = sorted(rrf_scores, key=lambda ck: rrf_scores[ck], reverse=True)
    return [key_to_item[ck] for ck in sorted_keys[:top_k]]


def hybrid_search(
    query: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """
    混合检索主入口。

    流程：
      1. Dense 检索（ChromaDB 余弦相似度）→ Top-M 候选
      2. Sparse 检索（BM25 关键词）→ Top-M 候选
      3. RRF 融合 → 最终 Top-K

    RETRIEVAL_MODE=dense 时跳过 BM25，等同于当前行为。
    """
    mode = current_app.config.get("RETRIEVAL_MODE", "hybrid")
    dense_candidates = current_app.config.get("DENSE_CANDIDATES", 10)
    sparse_candidates = current_app.config.get("BM25_CANDIDATES", 10)
    rrf_k = current_app.config.get("RRF_K", 60)

    # 1. Dense 检索
    dense_results = search_similar(
        query, top_k=dense_candidates, document_ids=document_ids
    )

    # 纯向量模式 → 归一化后返回
    if mode == "dense":
        return _normalize_relevance_scores(dense_results[:top_k])

    # 2. Sparse 检索
    bm25 = get_bm25_index()
    sparse_results: list[dict] = []
    if not bm25.is_empty:
        sparse_results = bm25.search(
            query, top_k=sparse_candidates, document_ids=document_ids
        )

    # 3. RRF 融合 + 归一化
    fused = rrf_fuse(dense_results, sparse_results, k=rrf_k, top_k=top_k)
    fused = _normalize_relevance_scores(fused)

    logger.debug(
        "混合检索: query=%r, mode=%s, dense=%d, sparse=%d, fused=%d",
        query[:60], mode, len(dense_results), len(sparse_results), len(fused),
    )
    return fused
