"""多环境配置 — dev / test / prod

环境变量优先级：.env 文件 < 系统环境变量
通过 FLASK_ENV 环境变量选择配置类。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    """基础配置，各环境共用"""

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')

    # ---- 日志 ----
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # ---- 数据库 ----
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR}/data.db',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- CORS ----
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # ---- 文件上传 ----
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

    # ---- 向量模型 (Embedding) ----
    # 阿里云百炼 text-embedding-v4，与 LLM 配置完全独立
    EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'bailian')
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-v4')
    EMBEDDING_API_URL = os.getenv('EMBEDDING_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    EMBEDDING_API_KEY = os.getenv('EMBEDDING_API_KEY', '')
    EMBEDDING_SIMILARITY_THRESHOLD = float(os.getenv('EMBEDDING_SIMILARITY_THRESHOLD', '0.3'))

    # ---- 大模型 (LLM) — DeepSeek ----
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
    LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'deepseek-chat')
    LLM_API_URL = os.getenv('LLM_API_URL', 'https://api.deepseek.com/v1')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '3'))

    # ---- RAG 参数 ----
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '800'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))
    TOP_K_DEFAULT = int(os.getenv('TOP_K_DEFAULT', '5'))

    # ---- 混合检索参数 ----
    RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'hybrid')       # dense | hybrid
    DENSE_CANDIDATES = int(os.getenv('DENSE_CANDIDATES', '10'))   # 向量召回数
    BM25_CANDIDATES = int(os.getenv('BM25_CANDIDATES', '10'))     # BM25 召回数
    RRF_K = int(os.getenv('RRF_K', '60'))                         # RRF 平滑参数

    # ---- ChromaDB ----
    CHROMA_PERSIST_DIR = os.getenv(
        'CHROMA_PERSIST_DIR',
        str(BASE_DIR / 'chroma_data'),
    )


class DevConfig(BaseConfig):
    """开发环境"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestConfig(BaseConfig):
    """测试环境"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProdConfig(BaseConfig):
    """生产环境"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


# 配置映射
_config_map: dict[str, type[BaseConfig]] = {
    'development': DevConfig,
    'dev': DevConfig,
    'testing': TestConfig,
    'test': TestConfig,
    'production': ProdConfig,
    'prod': ProdConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    """根据环境名返回配置类"""
    if name is None:
        name = os.getenv('FLASK_ENV', 'development')
    return _config_map.get(name, DevConfig)
