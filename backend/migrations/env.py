"""Flask-Migrate 迁移环境"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from flask import current_app

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标元数据
from app.extensions import db
target_metadata = db.metadata


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url') or current_app.config.get('SQLALCHEMY_DATABASE_URI')
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with current_app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
