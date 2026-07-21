"""资料管理路由 — 上传异步流水线 + 列表/详情/删除"""

import logging
import os
import threading
from pathlib import Path
from flask import Blueprint, request, current_app
from ..extensions import db
from ..models.models import Document, Chunk
from ..services.parser import parse_document
from ..services.chunker import chunk_document
from ..services.embedding import insert_chunks, delete_by_document
from ..services.keyword_search import get_bm25_index
from ..utils.helpers import generate_id, file_hash, allowed_file, json_response

logger = logging.getLogger(__name__)

documents_bp = Blueprint('documents', __name__)


def _process_document_async(app, doc_id: str, file_path_str: str, file_type: str, document_name: str) -> None:
    """后台异步流水线：解析 → 分块 → 向量化 → 更新状态"""
    with app.app_context():
        try:
            # 1. 解析文本
            file_path = Path(file_path_str)
            full_text, pages = parse_document(file_path, file_type)

            # 2. 文本分块
            chunk_size = app.config.get('CHUNK_SIZE', 800)
            chunk_overlap = app.config.get('CHUNK_OVERLAP', 100)
            chunks = chunk_document(
                full_text=full_text,
                pages=pages,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                document_id=doc_id,
                document_name=document_name,
            )

            # 3. 向量化 + 存入 ChromaDB
            chroma_ids = insert_chunks(chunks)

            # 4. 写入 SQLite chunks 表
            for i, chunk_dict in enumerate(chunks):
                db.session.add(Chunk(
                    id=generate_id('chk_'),
                    document_id=doc_id,
                    chunk_index=chunk_dict['chunk_index'],
                    content=chunk_dict['content'],
                    chroma_id=chroma_ids[i] if i < len(chroma_ids) else '',
                    page_number=chunk_dict.get('page_number'),
                    section_title=chunk_dict.get('section_title'),
                    token_count=chunk_dict.get('token_count'),
                ))

            # 5. 更新资料状态
            doc = Document.query.get(doc_id)
            if doc:
                doc.status = 'ready'
                doc.chunk_count = len(chunks)

            db.session.commit()

            # 6. 写入 BM25 关键词索引
            get_bm25_index().add_chunks(chunks)

        except Exception as e:
            logger.error('文档解析流水线失败 (id=%s): %s', doc_id_from_thread, e, exc_info=True)
            doc = Document.query.get(doc_id)
            if doc:
                doc.status = 'error'
                doc.error_message = str(e)
            db.session.commit()


@documents_bp.route('/documents/upload', methods=['POST'])
def upload_document():
    """上传文件 → 异步流水线 → 立即返回"""
    if 'file' not in request.files:
        return json_response(code=1001, message='未上传文件', status=400)

    file = request.files['file']
    if not file.filename:
        return json_response(code=1001, message='文件名为空', status=400)

    if not allowed_file(file.filename):
        return json_response(code=1001, message=f'不支持的文件格式: {Path(file.filename).suffix}，仅支持 PDF/PPT/Word/MD/TXT', status=400)

    # 保存文件
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'backend/uploads')
    os.makedirs(upload_folder, exist_ok=True)

    file_type = Path(file.filename).suffix.lower().lstrip('.')
    doc_id = generate_id('doc_')
    saved_name = f'{doc_id}.{file_type}'
    save_path = os.path.join(upload_folder, saved_name)
    file.save(save_path)

    file_size = os.path.getsize(save_path)

    # 写入数据库
    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        file_path=save_path,
        file_hash=file_hash(Path(save_path)),
        status='processing',
        chunk_count=0,
    )
    db.session.add(doc)
    db.session.commit()

    # 启动后台异步处理
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_process_document_async,
        args=(app, doc_id, save_path, file_type, file.filename),
        daemon=True,
    )
    thread.start()

    return json_response(code=0, data=doc.to_dict(), status=201)


@documents_bp.route('/documents', methods=['GET'])
def list_documents():
    """获取资料列表（分页）"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    status_filter = request.args.get('status', '')

    query = Document.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    query = query.order_by(Document.created_at.desc())

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [doc.to_dict() for doc in pagination.items]

    return json_response(code=0, data={
        'total': pagination.total,
        'items': items,
    })


@documents_bp.route('/documents/<document_id>', methods=['GET'])
def get_document(document_id: str):
    """获取单个资料详情"""
    doc = Document.query.get(document_id)
    if doc is None:
        return json_response(code=1002, message=f'资料 {document_id} 不存在', status=404)
    return json_response(code=0, data=doc.to_dict())


@documents_bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id: str):
    """级联删除：文件 + ChromaDB 向量 + 数据库记录"""
    doc = Document.query.get(document_id)
    if doc is None:
        return json_response(code=1002, message=f'资料 {document_id} 不存在', status=404)

    # 1. 删除 ChromaDB 向量
    try:
        delete_by_document(document_id)
    except Exception:
        pass

    # 1.5 删除 BM25 关键词索引
    get_bm25_index().remove_by_document(document_id)

    # 2. 删除数据库 chunks（级联自动，但显式清理保证）
    Chunk.query.filter_by(document_id=document_id).delete()

    # 3. 删除本地文件
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError:
        pass

    # 4. 删除数据库记录
    chunk_count = doc.chunk_count
    db.session.delete(doc)
    db.session.commit()

    return json_response(code=0, data={
        'message': f'删除成功（已清理 {chunk_count} 个文本块和 {chunk_count} 条向量数据）',
    })


@documents_bp.route('/documents/<document_id>/reparse', methods=['POST'])
def reparse_document(document_id: str):
    """重新解析：清空已有数据 → 重新触发异步流水线"""
    doc = Document.query.get(document_id)
    if doc is None:
        return json_response(code=1002, message=f'资料 {document_id} 不存在', status=404)

    # 1. 清空旧向量
    try:
        delete_by_document(document_id)
    except Exception:
        pass

    # 2. 清空旧 chunks
    Chunk.query.filter_by(document_id=document_id).delete()
    db.session.commit()

    # 3. 重置状态
    doc.status = 'processing'
    doc.chunk_count = 0
    doc.error_message = None
    db.session.commit()

    # 4. 启动后台异步处理
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_process_document_async,
        args=(app, doc.id, doc.file_path, doc.file_type, doc.filename),
        daemon=True,
    )
    thread.start()

    return json_response(code=0, data=doc.to_dict())
