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


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(get_config(config_name))

    # 初始化日志（必须在其他操作之前）
    _setup_logging(app)

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
