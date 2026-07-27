"""Flask 应用工厂入口"""

import logging
import sys
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from .config import get_config
from .extensions import db, migrate


def _setup_logging(app: Flask):
    """配置统一日志格式：时间 | 级别 | 模块 | 消息"""
    level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
        datefmt='%H:%M:%S',
    ))

    # 根 logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Flask 自己也用这套
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)

    # 抑制 werkzeug 的每条请求日志（太吵），只保留 warn+
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    app.logger.info('日志系统初始化完成，级别=%s', logging.getLevelName(level))


def _validate_production_config(app: Flask):
    """生产环境强制校验：禁止 CORS 全开放和默认 SECRET_KEY"""
    if app.config.get('DEBUG', False) or app.config.get('TESTING', False):
        return  # 开发/测试环境跳过

    errors = []
    if app.config.get('CORS_ORIGINS') == ['*']:
        errors.append('生产环境不允许 CORS_ORIGINS="*"，请在 .env 中配置具体白名单（如 http://localhost:5173）')
    if app.config.get('SECRET_KEY') == 'dev-secret-change-in-production':
        errors.append('生产环境必须设置 SECRET_KEY 环境变量')

    if errors:
        for msg in errors:
            app.logger.error(msg)
        raise ValueError('\n'.join(errors))


def _run_migrations(app: Flask):
    """轻量 schema 迁移 — 为已有数据库添加新列（SQLite ALTER TABLE 兼容）

    使用 SQLAlchemy 原生连接执行，避免路径解析问题。
    """
    from sqlalchemy import text, inspect
    try:
        # 用 SQLAlchemy inspector 检查列是否存在（跨数据库兼容）
        inspector = inspect(db.engine)
        existing_cols = [col['name'] for col in inspector.get_columns('chat_sessions')]

        if 'document_ids' not in existing_cols:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN document_ids TEXT DEFAULT '[]'"))
                conn.commit()
            app.logger.info('✅ 迁移: chat_sessions 表已添加 document_ids 列')
    except Exception as e:
        # 不能静默失败 —— 记录完整错误信息
        app.logger.error('❌ 数据库迁移失败 (document_ids 列): %s', e, exc_info=True)


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(get_config(config_name))

    # 初始化日志（必须在其他操作之前）
    _setup_logging(app)

    # 生产环境安全检查
    _validate_production_config(app)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']))

    # 注册蓝图
    from .routes.documents import documents_bp
    from .routes.chat import chat_bp
    from .routes.quiz import quiz_bp
    from .routes.progress import progress_bp
    from .routes.report import report_bp
    from .routes.vectordb import vectordb_bp

    app.register_blueprint(documents_bp, url_prefix='/api/v1')
    app.register_blueprint(chat_bp, url_prefix='/api/v1')
    app.register_blueprint(quiz_bp, url_prefix='/api/v1')
    app.register_blueprint(progress_bp, url_prefix='/api/v1')
    app.register_blueprint(report_bp, url_prefix='/api/v1')
    app.register_blueprint(vectordb_bp, url_prefix='/api/v1')

    # 健康检查
    @app.route('/api/v1/health')
    def health():
        return {'code': 0, 'data': {'status': 'ok'}}

    # 数据库初始化（开发环境自动建表）
    with app.app_context():
        from .models.models import (
            Document, Chunk, ChatSession, ChatMessage,
            Quiz, QuizQuestion, QuizAnswer,
            KnowledgePoint, WeeklyReport, Setting
        )
        db.create_all()

        # 数据库 schema 迁移（已有数据库升级用）
        _run_migrations(app)

        # BM25 关键词索引初始化（从 SQLite chunks 表全量重建）
        try:
            from .services.keyword_search import init_bm25_index
            all_chunks = Chunk.query.all()
            if all_chunks:
                chunk_dicts = [
                    {
                        "content": c.content,
                        "document_id": c.document_id,
                        "document_name": getattr(c.document, "filename", "") if c.document else "",
                        "page_number": c.page_number,
                        "chunk_index": c.chunk_index,
                        "token_count": c.token_count,
                    }
                    for c in all_chunks
                ]
                init_bm25_index(chunk_dicts)
            app.logger.info("BM25 索引已就绪（chunk 数: %d）", len(all_chunks))
        except Exception as e:
            app.logger.warning("BM25 索引初始化跳过: %s", e)

    return app
