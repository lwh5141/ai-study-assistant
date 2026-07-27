"""对话路由 — RAG 问答 + SSE 流式 + 会话管理"""

import re
import json
import logging
from flask import Blueprint, current_app, request, Response, stream_with_context
from ..extensions import db
from ..models.models import ChatSession, ChatMessage
from ..services.rag import rag_query
from ..utils.helpers import generate_id, json_response

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)


def _extract_sources(content: str) -> tuple[str, list[dict]]:
    """从 SSE 流末尾提取 sources 标记"""
    match = re.search(r'<!--SOURCES:(.*?)-->', content)
    if match:
        sources_json = match.group(1)
        clean_content = content[:match.start()].strip()
        try:
            sources = json.loads(sources_json)
            return clean_content, sources
        except json.JSONDecodeError:
            return clean_content, []
    return content, []


@chat_bp.route('/chat', methods=['POST'])
def send_message():
    """RAG 对话 — 支持 SSE 流式输出"""
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return json_response(code=1001, message='消息不能为空', status=400)

    session_id = data.get('session_id', '')
    document_ids = data.get('document_ids')
    top_k = current_app.config.get('TOP_K_DEFAULT', 5)
    accept_sse = 'text/event-stream' in request.headers.get('Accept', '')

    # 获取或创建会话
    if session_id:
        session = ChatSession.query.get(session_id)
        if not session:
            return json_response(code=1002, message='会话不存在', status=404)
    else:
        session = ChatSession(id=generate_id('sess_'), title=message[:30])
        db.session.add(session)

    # 保存用户消息
    user_msg = ChatMessage(
        id=generate_id('msg_'),
        session_id=session.id,
        role='user',
        content=message,
    )
    db.session.add(user_msg)

    # 持久化该会话引用的资料 ID（新会话或资料变更时更新）
    if document_ids is not None:
        session.document_ids = json.dumps(document_ids, ensure_ascii=False)

    db.session.commit()

    # 提取 session_id 避免生成器内访问已断开的 ORM 对象
    sid = session.id

    if accept_sse:
        # === SSE 流式响应 ===
        def generate():
            full_content = ''
            sources_detected = False
            try:
                # 加载历史
                history = (
                    ChatMessage.query
                    .filter_by(session_id=sid)
                    .order_by(ChatMessage.created_at.asc())
                    .all()
                )
                chat_history = [{'role': m.role, 'content': m.content} for m in history[:-1]]

                for token in rag_query(message, top_k=top_k, document_ids=document_ids, chat_history=chat_history):
                    full_content += token

                    # 检测到 SOURCES 标记后停止向前端发送 token
                    if not sources_detected and '<!--SOURCES:' in full_content:
                        sources_detected = True

                    if not sources_detected:
                        yield f'data: {json.dumps({"token": token})}\n\n'

                # 提取 sources
                clean_content, sources = _extract_sources(full_content)
                sources_json = json.dumps(sources, ensure_ascii=False)

                # 保存 AI 回复
                ai_msg = ChatMessage(
                    id=generate_id('msg_'),
                    session_id=sid,
                    role='assistant',
                    content=clean_content,
                    sources=sources_json,
                )
                db.session.add(ai_msg)
                db.session.commit()

                yield f'data: {json.dumps({"session_id": sid, "message_id": ai_msg.id, "sources": sources})}\n\n'
                yield 'data: [DONE]\n\n'

            except Exception as e:
                logger.error('SSE 流式生成失败: %s', e, exc_info=True)
                error_content = f'抱歉，生成回答时出错：{str(e)}'
                yield f'data: {json.dumps({"token": error_content})}\n\n'
                yield 'data: [DONE]\n\n'
                # 错误时也保存
                ai_msg = ChatMessage(
                    id=generate_id('msg_'),
                    session_id=sid,
                    role='assistant',
                    content=full_content or error_content,
                    sources='[]',
                )
                db.session.add(ai_msg)
                db.session.commit()

        return Response(
            stream_with_context(generate()),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )
    else:
        # === 非流式（收集完整回答后返回） ===
        try:
            # 加载历史
            history = (
                ChatMessage.query
                .filter_by(session_id=sid)
                .order_by(ChatMessage.created_at.asc())
                .all()
            )
            chat_history = [{'role': m.role, 'content': m.content} for m in history[:-1]]

            full_content = ''
            for token in rag_query(message, top_k=top_k, document_ids=document_ids, chat_history=chat_history):
                full_content += token

            clean_content, sources = _extract_sources(full_content)

            # 保存
            ai_msg = ChatMessage(
                id=generate_id('msg_'),
                session_id=sid,
                role='assistant',
                content=clean_content,
                sources=json.dumps(sources, ensure_ascii=False),
            )
            db.session.add(ai_msg)
            db.session.commit()

            return json_response(code=0, data={
                'session_id': session.id,
                'message_id': ai_msg.id,
                'role': 'assistant',
                'content': clean_content,
                'sources': sources,
                'created_at': ai_msg.created_at,
            })
        except Exception as e:
            logger.error('非流式对话失败: %s', e, exc_info=True)
            return json_response(code=9999, message=str(e), status=500)


@chat_bp.route('/chat/sessions', methods=['GET'])
def list_sessions():
    sessions = ChatSession.query.order_by(ChatSession.updated_at.desc()).all()
    return json_response(code=0, data=[s.to_dict() for s in sessions])


@chat_bp.route('/chat/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    session = ChatSession.query.get(session_id)
    if not session:
        return json_response(code=1002, message='会话不存在', status=404)

    messages = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return json_response(code=0, data={
        'session_id': session.id,
        'title': session.title,
        'document_ids': json.loads(session.document_ids or '[]'),
        'messages': [m.to_dict() for m in messages],
    })


@chat_bp.route('/chat/sessions/<session_id>', methods=['PUT'])
def rename_session(session_id: str):
    """重命名会话"""
    session = ChatSession.query.get(session_id)
    if not session:
        return json_response(code=1002, message='会话不存在', status=404)

    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    if not title:
        return json_response(code=1001, message='标题不能为空', status=400)

    session.title = title
    db.session.commit()

    return json_response(code=0, data=session.to_dict())


@chat_bp.route('/chat/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    session = ChatSession.query.get(session_id)
    if not session:
        return json_response(code=1002, message='会话不存在', status=404)

    ChatMessage.query.filter_by(session_id=session_id).delete()
    db.session.delete(session)
    db.session.commit()

    return json_response(code=0, data={'message': '会话已删除'})
