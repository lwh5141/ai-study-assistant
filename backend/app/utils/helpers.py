"""工具函数"""

import hashlib
import uuid
from pathlib import Path


def generate_id(prefix: str = '') -> str:
    """生成短 UUID ID"""
    uid = uuid.uuid4().hex[:8]
    return f'{prefix}{uid}' if prefix else uid


def file_hash(file_path: Path) -> str:
    """计算文件 SHA-256"""
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    if size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    return f'{size_bytes / (1024 * 1024):.1f} MB'


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    allowed = {'.pdf', '.ppt', '.pptx', '.md', '.doc', '.docx', '.txt'}
    ext = Path(filename).suffix.lower()
    return ext in allowed


def json_response(code: int = 0, data=None, message: str = '', status: int = 200):
    """统一 JSON 响应构造（werkzeug 风格）"""
    from flask import jsonify
    body = {'code': code}
    if data is not None:
        body['data'] = data
    if message:
        body['message'] = message
    return jsonify(body), status
