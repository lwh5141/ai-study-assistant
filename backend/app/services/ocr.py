"""OCR 服务 — 使用 PaddleOCR 本地识别图片中的文字

首次运行会自动下载模型文件（~100MB），请确保网络畅通。
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

_ocr: Optional[object] = None
_init_success: Optional[bool] = None


def _get_ocr():
    """懒加载 PaddleOCR，仅初始化一次"""
    global _ocr, _init_success
    if _init_success is False:
        return None
    if _ocr is not None:
        return _ocr
    try:
        from paddleocr import PaddleOCR
        # PaddleOCR 3.x 移除了 show_log，2.x 保留，自适应兼容
        try:
            _ocr = PaddleOCR(lang='ch', use_angle_cls=True)
        except TypeError:
            _ocr = PaddleOCR(lang='ch', use_angle_cls=True, show_log=False)
        _init_success = True
        return _ocr
    except ImportError:
        _init_success = False
        logger.warning('PaddleOCR 未安装，跳过图片识别')
        return None
    except Exception as e:
        _init_success = False
        logger.error('PaddleOCR 初始化失败: %s', e)
        return None


def _image_bytes_to_pil(data: bytes) -> Optional[Image.Image]:
    """将各种格式的图片字节转为 PIL Image"""
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode == 'CMYK':
            img = img.convert('RGB')
        elif img.mode == 'RGBA':
            img = img.convert('RGB')
        elif img.mode == 'P':
            img = img.convert('RGB')
        elif img.mode == 'L':
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    except Exception:
        return None


def ocr_images(image_list: list[bytes]) -> str:
    """批量 OCR 识别图片，返回所有识别文本的拼接结果

    每张图片的结果用 [图片内容:] 前缀标记。

    返回空字符串表示无有效内容或 OCR 不可用。
    """
    ocr = _get_ocr()
    if ocr is None:
        return ''

    results: list[str] = []

    for idx, data in enumerate(image_list):
        try:
            img = _image_bytes_to_pil(data)
            if img is None:
                continue

            # 小图跳过（图标、装饰元素等）
            if img.width < 50 or img.height < 50:
                continue

            # 写入临时文件（PaddleOCR 需要文件路径）
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                img.save(f, format='PNG')
                tmp_path = f.name

            try:
                # PaddleOCR 3.x 移除了 cls 参数
                try:
                    ocr_result = ocr.ocr(tmp_path)
                except TypeError:
                    ocr_result = ocr.ocr(tmp_path, cls=True)
                if ocr_result and ocr_result[0]:
                    texts = []
                    for line in ocr_result[0]:
                        if line and len(line) > 1:
                            text = line[1][0]
                            if text.strip():
                                texts.append(text.strip())
                    if texts:
                        label = f'[图片内容 {idx + 1}]\n' if len(image_list) > 1 else '[图片内容]\n'
                        results.append(label + '\n'.join(texts))
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError as e:
                    logger.warning('OCR 清理临时文件失败 (%s): %s', tmp_path, e)

        except Exception as e:
            logger.warning('OCR 图片 %d 识别失败: %s', idx, e)
            continue

    return '\n\n'.join(results) if results else ''
