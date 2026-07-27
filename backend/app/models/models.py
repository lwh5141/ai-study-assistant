"""数据库模型 — 10 张表，严格匹配 docs/requirements.md 三、数据库表设计"""

import json
import uuid
from datetime import datetime, timezone
from ..extensions import db


def _pk_uuid(prefix: str = '') -> str:
    """生成带前缀的主键 ID"""
    uid = uuid.uuid4().hex[:8]
    return f'{prefix}{uid}' if prefix else uid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 3.1 documents — 资料表
# ============================================================
class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('doc_'))
    filename = db.Column(db.Text, nullable=False)
    file_type = db.Column(db.Text, nullable=False)  # pdf / ppt / pptx / md / doc / docx / txt
    file_size = db.Column(db.Integer, nullable=False, default=0)
    file_path = db.Column(db.Text, nullable=False)
    file_hash = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, nullable=False, default='processing')  # processing / ready / error
    chunk_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.Text, nullable=False, default=_now)
    updated_at = db.Column(db.Text, nullable=False, default=_now, onupdate=_now)

    # 索引
    __table_args__ = (
        db.Index('idx_documents_status', 'status'),
        db.Index('idx_documents_file_hash', 'file_hash'),
        db.Index('idx_documents_created_at', 'created_at'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'status': self.status,
            'chunk_count': self.chunk_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'error_message': self.error_message,
        }


# ============================================================
# 3.2 chunks — 文本块表
# ============================================================
class Chunk(db.Model):
    __tablename__ = 'chunks'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('chk_'))
    document_id = db.Column(db.Text, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    chroma_id = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    section_title = db.Column(db.Text, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.Text, nullable=False, default=_now)

    __table_args__ = (
        db.Index('idx_chunks_document_id', 'document_id'),
        db.Index('idx_chunks_chroma_id', 'chroma_id'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'chroma_id': self.chroma_id,
            'page_number': self.page_number,
            'section_title': self.section_title,
            'token_count': self.token_count,
            'created_at': self.created_at,
        }


# ============================================================
# 3.3 chat_sessions — 对话会话表
# ============================================================
class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('sess_'))
    title = db.Column(db.Text, nullable=True, default='新对话')
    document_ids = db.Column(db.Text, nullable=True, default='[]')  # JSON 数组，记录该会话引用的资料 ID
    created_at = db.Column(db.Text, nullable=False, default=_now)
    updated_at = db.Column(db.Text, nullable=False, default=_now, onupdate=_now)

    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_chat_sessions_updated_at', 'updated_at'),
    )

    def to_dict(self) -> dict:
        first_msg = (
            ChatMessage.query
            .filter_by(session_id=self.id, role='user')
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        preview = (first_msg.content[:60] + '…') if first_msg and len(first_msg.content) > 60 else (first_msg.content if first_msg else '')
        # 解析 document_ids 为列表
        try:
            doc_ids = json.loads(self.document_ids or '[]')
        except (json.JSONDecodeError, TypeError):
            doc_ids = []
        return {
            'session_id': self.id,
            'title': self.title,
            'document_ids': doc_ids,
            'message_count': self.messages.count(),
            'preview': preview,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


# ============================================================
# 3.4 chat_messages — 对话消息表
# ============================================================
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('msg_'))
    session_id = db.Column(db.Text, db.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Text, nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True, default='[]')  # JSON 数组
    created_at = db.Column(db.Text, nullable=False, default=_now)

    __table_args__ = (
        db.Index('idx_chat_messages_session_id', 'session_id'),
    )

    def to_dict(self) -> dict:
        import json
        try:
            parsed_sources = json.loads(self.sources) if self.sources else []
        except (json.JSONDecodeError, TypeError):
            parsed_sources = []
        return {
            'message_id': self.id,
            'role': self.role,
            'content': self.content,
            'sources': parsed_sources,
            'created_at': self.created_at,
        }


# ============================================================
# 3.5 quizzes — 测评记录表
# ============================================================
class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('quiz_'))
    title = db.Column(db.Text, nullable=False)
    question_count = db.Column(db.Integer, nullable=False, default=10)
    document_ids = db.Column(db.Text, nullable=True, default='[]')  # JSON 数组
    status = db.Column(db.Text, nullable=False, default='ready')  # ready / submitted
    total_score = db.Column(db.Float, nullable=True)
    correct_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.Text, nullable=False, default=_now)
    submitted_at = db.Column(db.Text, nullable=True)

    questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    answers = db.relationship('QuizAnswer', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_quizzes_status', 'status'),
        db.Index('idx_quizzes_created_at', 'created_at'),
    )

    def to_dict(self) -> dict:
        return {
            'quiz_id': self.id,
            'title': self.title,
            'question_count': self.question_count,
            'status': self.status,
            'score': self.total_score,
            'accuracy': (self.correct_count / self.question_count) if self.correct_count is not None and self.question_count > 0 else None,
            'created_at': self.created_at,
            'submitted_at': self.submitted_at,
        }


# ============================================================
# 3.6 quiz_questions — 测评题目表
# ============================================================
class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('q_'))
    quiz_id = db.Column(db.Text, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    type = db.Column(db.Text, nullable=False)  # choice / true_false / short_answer
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True, default='[]')  # JSON 数组
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    source_document_id = db.Column(db.Text, nullable=True)
    source_chunk_id = db.Column(db.Text, nullable=True)
    source_page = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.Text, nullable=False, default=_now)

    __table_args__ = (
        db.Index('idx_quiz_questions_quiz_id', 'quiz_id'),
    )

    def to_dict(self, include_answer: bool = False) -> dict:
        import json
        # 反序列化 options JSON 字符串为对象数组
        try:
            parsed_options = json.loads(self.options) if self.options else []
        except (json.JSONDecodeError, TypeError):
            parsed_options = []

        data = {
            'question_id': self.id,
            'index': self.question_index,
            'type': self.type,
            'content': self.content,
            'options': parsed_options,
            'source_document': self.source_document_id,
            'source_page': self.source_page,
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
        return data


# ============================================================
# 3.7 quiz_answers — 答题记录表
# ============================================================
class QuizAnswer(db.Model):
    __tablename__ = 'quiz_answers'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('ans_'))
    quiz_id = db.Column(db.Text, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Text, db.ForeignKey('quiz_questions.id', ondelete='CASCADE'), nullable=False)
    user_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=True)
    score = db.Column(db.Float, nullable=True)
    submitted_at = db.Column(db.Text, nullable=False, default=_now)

    __table_args__ = (
        db.UniqueConstraint('quiz_id', 'question_id', name='uq_quiz_answers_question'),
    )


# ============================================================
# 3.8 knowledge_points — 知识点掌握表
# ============================================================
class KnowledgePoint(db.Model):
    __tablename__ = 'knowledge_points'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('kp_'))
    name = db.Column(db.Text, nullable=False)
    document_id = db.Column(db.Text, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    correct_count = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    mastery_level = db.Column(db.Float, nullable=False, default=0.0, server_default='0.0')
    last_tested_at = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.Text, nullable=False, default=_now)
    updated_at = db.Column(db.Text, nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        db.UniqueConstraint('name', 'document_id', name='uq_knowledge_points_name_doc'),
    )

    def to_dict(self) -> dict:
        return {
            'knowledge_point': self.name,
            'document_name': None,  # 由关联查询填充
            'mastery_level': self.mastery_level,
            'total_questions': self.total_questions,
            'correct_count': self.correct_count,
            'last_tested': self.last_tested_at,
        }


# ============================================================
# 3.9 weekly_reports — 周报表
# ============================================================
class WeeklyReport(db.Model):
    __tablename__ = 'weekly_reports'

    id = db.Column(db.Text, primary_key=True, default=lambda: _pk_uuid('rpt_'))
    week_start = db.Column(db.Text, nullable=False)
    week_end = db.Column(db.Text, nullable=False)
    content_json = db.Column(db.Text, nullable=False)  # 周报完整 JSON
    generated_at = db.Column(db.Text, nullable=False, default=_now)

    __table_args__ = (
        db.UniqueConstraint('week_start', 'week_end', name='uq_weekly_reports_week'),
    )

    def to_dict(self) -> dict:
        import json
        return {
            'id': self.id,
            'week_start': self.week_start,
            'week_end': self.week_end,
            'avg_score': json.loads(self.content_json).get('avg_score', 0) if self.content_json else 0,
            'quiz_count': json.loads(self.content_json).get('quiz_count', 0) if self.content_json else 0,
            'generated_at': self.generated_at,
        }


# ============================================================
# 3.10 settings — 系统设置表 (Key-Value)
# ============================================================
class Setting(db.Model):
    __tablename__ = 'settings'

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.Text, nullable=False, default=_now, onupdate=_now)
