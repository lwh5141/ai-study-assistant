"""向量数据库管理路由 — 知识块浏览 + 向量库统计"""

from flask import Blueprint, request
from sqlalchemy import func
from ..extensions import db
from ..models.models import Chunk, Document
from ..services.embedding import _get_client, _get_collection
from ..utils.helpers import generate_id, json_response

vectordb_bp = Blueprint('vectordb', __name__)


@vectordb_bp.route('/vectordb/chunks', methods=['GET'])
def list_chunks():
    """分页获取知识块列表，支持按资料筛选和内容搜索"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    document_id = request.args.get('document_id', '').strip()
    search = request.args.get('search', '').strip()

    query = Chunk.query

    if document_id:
        query = query.filter(Chunk.document_id == document_id)
    if search:
        query = query.filter(Chunk.content.ilike(f'%{search}%'))

    total = query.count()
    chunks = (
        query
        .order_by(Chunk.document_id, Chunk.chunk_index)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 关联文档名
    doc_ids = list({c.document_id for c in chunks})
    doc_map = {}
    if doc_ids:
        docs = Document.query.filter(Document.id.in_(doc_ids)).all()
        doc_map = {d.id: d.filename for d in docs}

    items = []
    for c in chunks:
        d = c.to_dict()
        d['document_name'] = doc_map.get(c.document_id, '(已删除)')
        items.append(d)

    return json_response(code=0, data={
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': items,
    })


@vectordb_bp.route('/vectordb/chunks/<chunk_id>', methods=['GET'])
def get_chunk(chunk_id: str):
    """获取单个知识块详情（完整内容）"""
    chunk = Chunk.query.get(chunk_id)
    if not chunk:
        return json_response(code=1002, message='知识块不存在', status=404)

    doc = Document.query.get(chunk.document_id)
    result = chunk.to_dict()
    result['document_name'] = doc.filename if doc else '(已删除)'
    return json_response(code=0, data=result)


@vectordb_bp.route('/vectordb/stats', methods=['GET'])
def get_stats():
    """向量库统计信息"""
    try:
        collection = _get_collection()
        count = collection.count()
    except Exception:
        # ChromaDB 尚未初始化或无数据
        count = 0

    # SQLite 中的总块数
    total_chunks = Chunk.query.count()

    # 按文档分布的块数
    doc_stats = (
        db.session.query(
            Document.id,
            Document.filename,
            func.count(Chunk.id).label('chunk_count'),
        )
        .outerjoin(Chunk, Document.id == Chunk.document_id)
        .group_by(Document.id)
        .order_by(func.count(Chunk.id).desc())
        .all()
    )

    by_document = [
        {
            'document_id': doc_id,
            'document_name': filename,
            'chunk_count': cnt,
        }
        for doc_id, filename, cnt in doc_stats
    ]

    # 平均 token 数
    avg_tokens = (
        db.session.query(func.avg(Chunk.token_count))
        .filter(Chunk.token_count.isnot(None))
        .scalar()
    )
    avg_tokens = round(avg_tokens, 1) if avg_tokens else 0

    return json_response(code=0, data={
        'collection_name': 'documents',
        'distance_metric': 'cosine',
        'chroma_count': count,
        'sqlite_count': total_chunks,
        'synced': count == total_chunks,
        'avg_tokens_per_chunk': avg_tokens,
        'embedding_model': 'text-embedding-v4 (阿里云百炼)',
        'by_document': by_document,
    })
