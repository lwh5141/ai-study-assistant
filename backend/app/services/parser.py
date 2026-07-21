"""文档解析服务 — PDF / PPT / Word / Markdown / TXT

每个解析器返回 (full_text: str, pages: list[dict])
pages[i] = {'page_number': int, 'text': str, 'section_title': str|None}

图片处理：各解析器会提取文档中的嵌入图片，通过本地 OCR 识别其中的文字，
并将结果以 [图片内容] 标记注入到原文对应位置。
"""

from pathlib import Path
from typing import Optional

import logging

logger = logging.getLogger(__name__)


# ---- OCR 集成（延迟导入，避免未安装时阻塞） ----

def _ocr_pdf_page_images(doc, page_index: int) -> str:
    """提取并 OCR 识别 PDF 单页中的所有图片"""
    try:
        from .ocr import ocr_images
    except ImportError:
        return ''

    try:
        page = doc[page_index]
        image_list = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base = doc.extract_image(xref)
            if base and base.get('image'):
                image_list.append(base['image'])
        if image_list:
            return ocr_images(image_list)
    except Exception as e:
        logger.warning('PDF 第 %d 页图片处理异常: %s', page_index + 1, e)
    return ''


def _ocr_pptx_slide_images(slide) -> str:
    """提取并 OCR 识别 PPT 单页幻灯片中的所有图片"""
    try:
        from .ocr import ocr_images
    except ImportError:
        return ''

    try:
        image_list = []
        for shape in slide.shapes:
            # shape_type=13 是 Picture
            if hasattr(shape, 'shape_type') and shape.shape_type == 13:
                try:
                    blob = shape.image.blob
                    if blob:
                        image_list.append(blob)
                except Exception:
                    pass
        if image_list:
            return ocr_images(image_list)
    except Exception as e:
        logger.warning('PPT 幻灯片图片处理异常: %s', e)
    return ''


def _ocr_docx_images(doc) -> str:
    """提取并 OCR 识别 DOCX 文档中的所有嵌入图片"""
    try:
        from .ocr import ocr_images
    except ImportError:
        return ''

    try:
        image_list = []
        for rel in doc.part.rels.values():
            if 'image' in rel.reltype:
                try:
                    blob = rel.target_part.blob
                    if blob:
                        image_list.append(blob)
                except Exception:
                    pass
        if image_list:
            return ocr_images(image_list)
    except Exception as e:
        logger.warning('DOCX 图片处理异常: %s', e)
    return ''


# ---- PDF 解析 ----

def parse_pdf(file_path: Path) -> tuple[str, list[dict]]:
    """PyMuPDF 提取 PDF 文本 + 图片 OCR，保留页码"""
    import fitz  # PyMuPDF

    doc = fitz.open(str(file_path))
    pages = []
    full_parts = []

    for i, page in enumerate(doc):
        text = page.get_text('text').strip()

        # OCR 识别页内图片
        ocr_text = _ocr_pdf_page_images(doc, i)

        if text or ocr_text:
            combined = text
            if ocr_text:
                combined = f'{text}\n\n{ocr_text}' if text else ocr_text
            pages.append({
                'page_number': i + 1,
                'text': combined,
                'section_title': None,
            })
            full_parts.append(combined)

    doc.close()
    return '\n\n'.join(full_parts), pages


# ---- PPT 解析 ----

def parse_ppt(file_path: Path) -> tuple[str, list[dict]]:
    """python-pptx 提取幻灯片文本 + 图片 OCR，保留页号与标题"""
    from pptx import Presentation

    prs = Presentation(str(file_path))
    pages = []
    full_parts = []

    for i, slide in enumerate(prs.slides):
        lines = []
        title = None

        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue
                    if title is None:
                        title = text
                    lines.append(text)

        # OCR 识别幻灯片内图片
        ocr_text = _ocr_pptx_slide_images(slide)
        if ocr_text:
            lines.append('\n' + ocr_text)

        if lines:
            page_text = '\n'.join(lines)
            pages.append({
                'page_number': i + 1,
                'text': page_text,
                'section_title': title,
            })
            full_parts.append(page_text)

    return '\n\n'.join(full_parts), pages


# ---- Word 解析 ----

def _parse_fallback_text(file_path: Path, source_type: str = '') -> tuple[str, list[dict]]:
    """降级方案：当作纯文本读取，按空行分页"""
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = file_path.read_text(encoding='gbk')

    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    pages = []
    for i, para in enumerate(paragraphs):
        pages.append({
            'page_number': i,
            'text': para,
            'section_title': None,
        })

    return content, pages


def parse_docx(file_path: Path) -> tuple[str, list[dict]]:
    """解析 .docx / .doc 文档：提取段落 + 表格 + 图片 OCR，按 Heading 分页"""
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    # 检测 .doc 旧格式
    ext = file_path.suffix.lower()
    if ext == '.doc':
        raise ValueError(
            '不支持旧版 .doc 格式（Word 2003 及更早）。'
            '请用 Microsoft Word 或 WPS 将文件另存为 .docx 格式后重新上传。'
        )

    try:
        doc = Document(str(file_path))
    except PackageNotFoundError:
        # 不是有效的 Open XML 格式，降级为纯文本解析
        return _parse_fallback_text(file_path, 'docx')
    except Exception as e:
        raise ValueError(f'Word 文档打开失败：{e}')

    all_lines: list[str] = []
    current_section: Optional[str] = None
    pages: list[dict] = []
    page_texts: list[str] = []
    current_page = 0

    def _flush_page():
        nonlocal current_page
        if page_texts:
            pages.append({
                'page_number': current_page,
                'text': '\n'.join(page_texts),
                'section_title': current_section,
            })
            current_page += 1
            page_texts.clear()

    # 1. 提取段落
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = (para.style.name if para.style else '')
        if style_name.startswith('Heading'):
            _flush_page()
            current_section = text

        page_texts.append(text)
        all_lines.append(text)

    # 2. 提取表格
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                line = ' | '.join(row_texts)
                page_texts.append(line)
                all_lines.append(line)

    # 3. OCR 识别文档内图片
    ocr_text = _ocr_docx_images(doc)
    if ocr_text:
        page_texts.append('\n' + ocr_text)
        all_lines.append(ocr_text)

    # 最后一页
    _flush_page()

    if not all_lines:
        raise ValueError('文档内容为空，未提取到任何文本')

    return '\n\n'.join(all_lines), pages


# ---- Markdown 解析 ----

def parse_markdown(file_path: Path) -> tuple[str, list[dict]]:
    """按标题层级拆分 Markdown"""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    pages = []
    page_texts: list[str] = []
    current_title: Optional[str] = None
    current_page = 0

    for line in lines:
        stripped = line.strip()
        # 检测标题行
        if stripped.startswith('#'):
            if page_texts:
                pages.append({
                    'page_number': current_page,
                    'text': '\n'.join(page_texts),
                    'section_title': current_title,
                })
            current_title = stripped.lstrip('#').strip()
            page_texts = []
            current_page += 1
        if stripped:
            page_texts.append(stripped)

    if page_texts:
        pages.append({
            'page_number': current_page,
            'text': '\n'.join(page_texts),
            'section_title': current_title,
        })

    return content, pages


# ---- TXT 解析 ----

def parse_txt(file_path: Path) -> tuple[str, list[dict]]:
    """读取纯文本，自动检测编码"""
    # 尝试 UTF-8，失败则尝试 GBK
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = file_path.read_text(encoding='gbk')

    # 按空行分页
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    pages = []
    current_page = 0

    for para in paragraphs:
        pages.append({
            'page_number': current_page,
            'text': para,
            'section_title': None,
        })
        current_page += 1

    return content, pages


# ---- 调度器 ----

PARSER_MAP = {
    'pdf': parse_pdf,
    'ppt': parse_ppt,
    'pptx': parse_ppt,
    'docx': parse_docx,
    'doc': parse_docx,  # .doc → 会被 parse_docx 开头拦截并给出提示
    'md': parse_markdown,
    'txt': parse_txt,
}


def parse_document(file_path: Path, file_type: str) -> tuple[str, list[dict]]:
    """根据文件类型分发到对应解析器"""
    parser = PARSER_MAP.get(file_type.lower())
    if parser is None:
        raise ValueError(f'不支持的文件类型: {file_type}')
    return parser(file_path)
