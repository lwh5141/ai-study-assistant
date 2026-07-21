"""向量化与检索服务 — 阿里云百炼 text-embedding-v4 + ChromaDB

API 文档: https://help.aliyun.com/zh/model-studio/text-embedding-api
兼容 OpenAI 接口格式，直接使用 openai 库调用 DashScope。
"""

import os
import math
from typing import Optional, Union, Any
import chromadb
from chromadb.config import Settings
from chromadb.api import ClientAPI
from openai import OpenAI
from flask import current_app


# ---- ChromaDB 客户端（懒加载） ----

_chroma_client: Optional[ClientAPI] = None
_collection: Optional[Any] = None


def _get_client() -> ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = current_app.config.get('CHROMA_PERSIST_DIR', 'backend/chroma_data')
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_collection() -> Any:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name='documents',
            metadata={'hnsw:space': 'cosine'},  # 余弦相似度
        )
    return _collection


# ---- 百炼 Embedding 客户端（懒加载） ----

_embedding_client: Optional[OpenAI] = None


def _get_embedding_client() -> OpenAI:
    global _embedding_client
    if _embedding_client is None:
        api_key = current_app.config.get('EMBEDDING_API_KEY', '')
        base_url = current_app.config.get('EMBEDDING_API_URL', '')
        if not api_key:
            raise RuntimeError('EMBEDDING_API_KEY 未配置，无法调用百炼 Embedding API')
        _embedding_client = OpenAI(api_key=api_key, base_url=base_url)
    return _embedding_client


# ---- 向量化 ----

def embed_text(text: str) -> list[float]:
    """单条文本向量化"""
    model = current_app.config.get('EMBEDDING_MODEL_NAME', 'text-embedding-v4')
    client = _get_embedding_client()
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def embed_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """批量向量化（百炼单次最多约 10 条，自动分批）"""
    if not texts:
        return []

    model = current_app.config.get('EMBEDDING_MODEL_NAME', 'text-embedding-v4')
    client = _get_embedding_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([d.embedding for d in response.data])
        # 批次间短暂间隔，避免限流
        if i + batch_size < len(texts):
            import time
            time.sleep(0.3)

    return all_embeddings


# ---- ChromaDB 存储 ----

def insert_chunks(chunks: list[dict]) -> list[str]:
    """将分块文本向量化后存入 ChromaDB，返回 chroma_id 列表"""
    if not chunks:
        return []

    texts = [c['content'] for c in chunks]
    embeddings = embed_batch(texts)

    collection = _get_collection()
    chroma_ids: list[str] = []
    metadatas: list[dict] = []

    for i, chunk in enumerate(chunks):
        cid = f"{chunk.get('document_id', 'unknown')}_chunk_{chunk['chunk_index']}"
        chroma_ids.append(cid)
        metadatas.append({
            'document_id': chunk.get('document_id', ''),
            'document_name': chunk.get('document_name', ''),
            'page_number': chunk.get('page_number') or 0,
            'section_title': chunk.get('section_title') or '',
            'chunk_index': chunk['chunk_index'],
            'token_count': chunk.get('token_count', 0),
        })

    collection.add(
        ids=chroma_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return chroma_ids


# ---- 相似度检索 ----

def search_similar(
    query: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """
    语义检索：query → embedding → ChromaDB 余弦相似度搜索 → 阈值过滤

    返回:
    [{
        'document_id': str,
        'document_name': str,
        'page': int,
        'chunk_index': int,
        'excerpt': str,
        'relevance_score': float,  # 0.0 - 1.0
    }]
    """
    threshold = current_app.config.get('EMBEDDING_SIMILARITY_THRESHOLD', 0.3)
    query_embedding = embed_text(query)
    collection = _get_collection()

    # 构建过滤条件
    where_filter = None
    if document_ids:
        where_filter = {'document_id': {'$in': document_ids}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=['documents', 'metadatas', 'distances'],
    )

    sources: list[dict] = []
    if results['ids'] and results['ids'][0]:
        for i, cid in enumerate(results['ids'][0]):
            # ChromaDB cosine distance → similarity = 1 - distance
            distance = results['distances'][0][i] if results['distances'] else 0
            similarity = 1.0 - distance

            if similarity < threshold:
                continue

            meta = results['metadatas'][0][i] if results['metadatas'] else {}
            doc_text = results['documents'][0][i] if results['documents'] else ''

            sources.append({
                'document_id': meta.get('document_id', ''),
                'document_name': meta.get('document_name', ''),
                'page': meta.get('page_number', 0),
                'chunk_index': meta.get('chunk_index', 0),
                'excerpt': doc_text[:500],  # 摘要截取前 500 字
                'relevance_score': round(similarity, 4),
            })

    return sources


# ---- 删除 ----

def delete_by_document(document_id: str):
    """删除指定资料的所有向量"""
    collection = _get_collection()
    try:
        # 获取该资料的所有 chroma_id
        results = collection.get(
            where={'document_id': document_id},
            include=[],
        )
        if results['ids']:
            collection.delete(ids=results['ids'])
    except Exception:
        pass  # 集合为空时不报错


# ---- 工具 ----

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def reset_globals():
    """重置全局客户端（测试用）"""
    global _chroma_client, _collection, _embedding_client
    _chroma_client = None
    _collection = None
    _embedding_client = None
