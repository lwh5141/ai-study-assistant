"""学习进度路由 — 总览 / 知识点掌握 / 薄弱分析"""

from flask import Blueprint, request
from ..extensions import db
from ..models.models import Document, Chunk, Quiz, KnowledgePoint
from ..utils.helpers import json_response

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/progress/overview', methods=['GET'])
def get_overview():
    """学习进度总览 — 聚合查询"""
    total_docs = Document.query.count()
    total_chunks = Chunk.query.count()
    quizzes = Quiz.query.filter_by(status='submitted').all()
    total_quizzes = len(quizzes)
    total_questions = sum(q.question_count for q in quizzes)
    avg_acc = (
        sum(q.correct_count / q.question_count for q in quizzes if q.correct_count is not None and q.question_count > 0)
        / total_quizzes if total_quizzes > 0 else 0
    )

    # 最近活跃时间
    last_doc = Document.query.order_by(Document.updated_at.desc()).first()
    last_quiz = Quiz.query.order_by(Quiz.submitted_at.desc()).first()
    last_activity = ''
    if last_doc and last_quiz:
        last_activity = max(last_doc.updated_at, last_quiz.submitted_at or '')
    elif last_doc:
        last_activity = last_doc.updated_at
    elif last_quiz:
        last_activity = last_quiz.submitted_at or ''

    # 本周学习天数（简化：有上传或测评的天数）
    study_days = _count_study_days_this_week()

    return json_response(code=0, data={
        'total_documents': total_docs,
        'total_quizzes': total_quizzes,
        'total_quiz_questions': total_questions,
        'avg_accuracy': round(avg_acc, 2),
        'study_days_this_week': study_days,
        'total_chunks': total_chunks,
        'last_activity': last_activity,
    })


@progress_bp.route('/progress/knowledge', methods=['GET'])
def get_knowledge_points():
    """知识点掌握情况 — 关联查询 knowledge_points + documents"""
    document_id = request.args.get('document_id', '')

    query = KnowledgePoint.query
    if document_id:
        query = query.filter_by(document_id=document_id)
    query = query.order_by(KnowledgePoint.mastery_level.asc())

    kps = query.limit(50).all()

    items = []
    for kp in kps:
        doc = Document.query.get(kp.document_id)
        items.append({
            'knowledge_point': kp.name,
            'document_name': doc.filename if doc else '未知',
            'mastery_level': kp.mastery_level,
            'total_questions': kp.total_questions,
            'correct_count': kp.correct_count,
            'last_tested': kp.last_tested_at,
        })

    return json_response(code=0, data=items)


@progress_bp.route('/progress/weak-points', methods=['GET'])
def get_weak_points():
    """薄弱知识点分析 — mastery < 0.6 且至少答过 2 题"""
    kps = (
        KnowledgePoint.query
        .filter(KnowledgePoint.mastery_level < 0.6)
        .filter(KnowledgePoint.total_questions >= 2)
        .order_by(KnowledgePoint.mastery_level.asc())
        .limit(10)
        .all()
    )

    items = []
    for kp in kps:
        doc = Document.query.get(kp.document_id)
        items.append({
            'knowledge_point': kp.name,
            'document_name': doc.filename if doc else '未知',
            'mastery_level': kp.mastery_level,
            'total_questions': kp.total_questions,
            'correct_count': kp.correct_count,
            'error_count': kp.total_questions - kp.correct_count,
            'last_tested': kp.last_tested_at,
        })

    return json_response(code=0, data=items)


def _count_study_days_this_week() -> int:
    """计算本周有学习活动的天数"""
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())

    # 本周上传的资料
    week_docs = Document.query.filter(
        Document.created_at >= monday.isoformat()
    ).count()

    # 本周测评（排除 submitted_at 为 NULL 的）
    week_quizzes = Quiz.query.filter(
        Quiz.submitted_at >= monday.isoformat(),
        Quiz.submitted_at.isnot(None),
    ).count()

    # 简化：有活动即为学习天数估算
    if week_docs == 0 and week_quizzes == 0:
        return 0
    return min(7, max(week_docs, week_quizzes) if max(week_docs, week_quizzes) <= 7 else 7)
