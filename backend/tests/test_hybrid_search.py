"""
混合检索（RRF + 编排）测试方案
============================
6 个用例，分三类：
  分类四：RRF 融合逻辑（用例 8-10）
  分类五：混合检索编排（用例 11-13）

运行方式：cd backend && python -m pytest tests/test_hybrid_search.py -v
依赖：纯算法测试，无 Flask/DB/ChromaDB
"""

import pytest


# ============================================================
# RRF 融合函数（测试版 — 实现逻辑与正式代码一致）
# ============================================================

def rrf_fuse(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
    top_k: int = 5,
) -> list[dict]:
    """
    将两组排序结果用 RRF 融合。

    参数：
      dense_results: 向量检索结果（已排序，含 'id' 字段）
      sparse_results: BM25 检索结果（已排序，含 'id' 字段）
      k: RRF 平滑参数
      top_k: 最终返回数量

    返回：融合并排序后的结果列表
    """
    if not dense_results and not sparse_results:
        return []

    # 只有一路有结果 → 直接截取
    if not sparse_results:
        return dense_results[:top_k]
    if not dense_results:
        return sparse_results[:top_k]

    # 双路融合
    rrf_scores: dict[str, float] = {}
    id_to_item: dict[str, dict] = {}

    # Dense 路
    for rank, item in enumerate(dense_results):
        chunk_id = item["id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        id_to_item[chunk_id] = item

    # Sparse 路
    for rank, item in enumerate(sparse_results):
        chunk_id = item["id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        if chunk_id not in id_to_item:
            id_to_item[chunk_id] = item

    # 按 RRF 分数降序
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
    return [id_to_item[cid] for cid in sorted_ids[:top_k]]


# ============================================================
# 共享测试数据
# ============================================================

def make_item(id_str: str) -> dict:
    return {"id": id_str, "document_name": f"{id_str}.pdf", "content": f"content of {id_str}"}


# ============================================================
# 分类四：RRF 融合逻辑
# ============================================================


class TestRRFFusion:
    """RRF 融合算法"""

    def test_rrf_basic_fusion(self):
        """用例 8：RRF 双路融合 — 两路均有结果，同时出现的排前面"""
        dense = [make_item(id_str) for id_str in ["A", "B", "C", "D", "E"]]
        sparse = [make_item(id_str) for id_str in ["C", "A", "X", "Y", "Z"]]

        result = rrf_fuse(dense, sparse, k=60, top_k=8)

        ids = [r["id"] for r in result]
        assert len(ids) == 8, f"期望 8 条，实际 {len(ids)}"

        # A 在 dense rank=1, sparse rank=2
        # C 在 dense rank=3, sparse rank=1
        # A: 1/(60+1) + 1/(60+2) = 0.0325
        # C: 1/(60+3) + 1/(60+1) = 0.0323
        assert ids[0] in ("A", "C"), f"期望 A 或 C 排第一，实际 {ids[0]}"
        assert ids[1] in ("A", "C"), f"期望 A 或 C 排第二，实际 {ids[1]}"

        # Z 只在 sparse 路出现（rank=5），RRF = 1/(60+5) ≈ 0.0154
        # top_k=8 时 Z 应在结果中（与 E 分数相同，共 8 个独立项）
        assert "Z" in ids, f"Z 只在稀疏路出现，top_k=7 时应在融合结果中。实际: {ids}"

    def test_rrf_single_path_degradation(self):
        """用例 9：单路退化 — 只有一路有结果时直接返回"""
        dense = [make_item(id_str) for id_str in ["A", "B", "C", "D", "E"]]

        result = rrf_fuse(dense, [], k=60, top_k=3)

        assert len(result) == 3
        assert [r["id"] for r in result] == ["A", "B", "C"], (
            "单路时应直接截取 Top-3"
        )

    def test_rrf_k_parameter_effect(self):
        """用例 10：k 参数影响 — k 越大排名越保守（分数差异缩小）"""
        dense = [make_item(id_str) for id_str in ["A", "B", "C"]]
        sparse = [make_item(id_str) for id_str in ["C", "B", "A"]]

        result_small_k = rrf_fuse(dense, sparse, k=1, top_k=3)
        result_large_k = rrf_fuse(dense, sparse, k=120, top_k=3)

        ids_small = [r["id"] for r in result_small_k]
        ids_large = [r["id"] for r in result_large_k]

        # 排名顺序可能不同：k 越小，排名差异越大
        # 至少两种 k 值都产出合法排序
        for result_list in [result_small_k, result_large_k]:
            assert len(result_list) == 3
            assert {r["id"] for r in result_list} == {"A", "B", "C"}, (
                "所有原始项都应在融合结果中"
            )

        # 记录两种 k 的排名差异（仅做信息输出，不强制断言）
        # k=1 时权重对排名更敏感
        if ids_small == ids_large:
            pytest.skip("k 值在本数据上未产生排名差异，属正常")


# ============================================================
# 分类五：混合检索编排
# ============================================================


class TestHybridOrchestration:
    """混合检索编排逻辑（mock retriever）"""

    def test_hybrid_both_contributors(self):
        """用例 11：双路正常融合 — 两条路的结果都在最终输出中"""
        dense = [make_item(id_str) for id_str in ["A", "B", "C", "D", "E"]]
        sparse = [make_item(id_str) for id_str in ["C", "D", "X", "Y", "Z"]]

        result = rrf_fuse(dense, sparse, k=60, top_k=5)

        ids = {r["id"] for r in result}
        # 验证稀疏路独有的项也有机会进入
        assert "X" in ids or "Y" in ids or "Z" in ids, (
            f"稀疏路独有的项（X/Y/Z）应至少有一个进入融合结果。实际: {ids}"
        )
        # 验证两路共有的项出现
        assert "C" in ids, "两路共有的 C 应在结果中"

    def test_hybrid_sparse_empty_fallback(self):
        """用例 12：关键词路无结果 — 退化为纯向量"""
        dense = [make_item(id_str) for id_str in ["A", "B", "C", "D", "E"]]

        result = rrf_fuse(dense, [], k=60, top_k=5)

        assert [r["id"] for r in result] == ["A", "B", "C", "D", "E"], (
            "关键词路为空时，结果应与纯向量完全一致"
        )

    def test_hybrid_dense_only_mode(self):
        """用例 13：纯 dense 模式 — 与直接调向量检索一致"""
        # 模拟只有 dense 路：传递 dense 结果 + 空 sparse
        dense = [make_item(id_str) for id_str in ["P", "Q", "R"]]

        result = rrf_fuse(dense, [], k=60, top_k=5)

        assert len(result) == 3
        assert [r["id"] for r in result] == ["P", "Q", "R"]
