"""pytest 配置 — 测试夹具"""

import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    """创建测试 app（内存数据库）"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()
