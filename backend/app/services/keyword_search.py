"""BM25 关键词检索 — jieba 分词 + rank-bm25 倒排索引

提供：
  BM25Index  — 索引构建、增删、搜索
  get_bm25_index() / init_bm25_index()  — 全局单例管理
"""

import logging
from jieba import cut as jieba_cut
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# 全局单例
_bm25_index: "BM25Index | None" = None


class BM25Index:
    """BM25 关键词检索索引。不支持增量操作，增/删后全量重建。"""

    def __init__(self):
        self._chunks: list[dict] = []
        self._bm25: BM25Okapi | None = None
        self._tokenized: list[list[str]] = []

    # ---- 构建 ----

    def build(self, chunks: list[dict]) -> None:
        """从 chunk 列表全量构建索引"""
        self._chunks = list(chunks)
        self._rebuild_bm25()
        logger.info("BM25 索引构建完成，chunk 数: %d", len(self._chunks))

    def _rebuild_bm25(self) -> None:
        """内部：重建 BM25Okapi 实例"""
        if not self._chunks:
            self._bm25 = None
            self._tokenized = []
            return
        self._tokenized = [list(jieba_cut(c.get("content", ""))) for c in self._chunks]
        self._bm25 = BM25Okapi(self._tokenized)

    # ---- 维护 ----

    def add_chunks(self, chunks: list[dict]) -> None:
        """添加 chunk 并重建索引"""
        self._chunks.extend(chunks)
        self._rebuild_bm25()
        logger.info("BM25 索引新增 %d chunk，总数: %d", len(chunks), len(self._chunks))

    def remove_by_document(self, document_id: str) -> int:
        """移除指定文档的所有 chunk 并重建索引，返回移除数量"""
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.get("document_id") != document_id]
        removed = before - len(self._chunks)
        self._rebuild_bm25()
        logger.info("BM25 索引移除文档 %s（%d chunk），剩余: %d", document_id, removed, len(self._chunks))
        return removed

    # ---- 搜索 ----

    def search(
        self,
        query: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        """BM25 搜索，返回相关 chunk（按 BM25 分数降序）"""
        if not self._bm25 or not query.strip():
            return []

        query_tokens = list(jieba_cut(query))
        scores = self._bm25.get_scores(query_tokens)

        # 收集非零分数
        candidates: list[tuple[int, float]] = []
        for i, score in enumerate(scores):
            if score <= 0:
                continue
            chunk = self._chunks[i]
            if document_ids and chunk.get("document_id") not in document_ids:
                continue
            candidates.append((i, score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        results: list[dict] = []
        for idx, score in candidates[:top_k]:
            chunk = self._chunks[idx]
            results.append({
                "document_id": chunk.get("document_id", ""),
                "document_name": chunk.get("document_name", ""),
                "page": chunk.get("page_number", 0),
                "chunk_index": chunk.get("chunk_index", 0),
                "excerpt": chunk.get("content", "")[:500],
                "relevance_score": round(float(score), 4),
            })

        return results

    @property
    def is_empty(self) -> bool:
        return self._bm25 is None

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


# ---- 全局单例 ----

def get_bm25_index() -> BM25Index:
    """返回全局 BM25Index 单例"""
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index


def init_bm25_index(chunks: list[dict]) -> BM25Index:
    """用给定 chunk 列表初始化/重建全局 BM25Index"""
    global _bm25_index
    _bm25_index = BM25Index()
    _bm25_index.build(chunks)
    return _bm25_index
