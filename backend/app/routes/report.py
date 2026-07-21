"""周报路由 — AI 生成 + 列表/详情 + 设置"""

import json
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, current_app
from ..extensions import db
from ..models.models import (
    WeeklyReport as WeeklyReportModel,
    Document, Quiz, KnowledgePoint, Setting,
)
from ..services.llm import chat_complete
from ..utils.helpers import generate_id, json_response

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)

# ---- 周报生成提示词 ----

REPORT_PROMPT = """你是一位学习分析师。请根据用户本周的学习数据，生成一份结构化的学习周报。

## 周报结构

1. **学习概况**：用 3-5 句话总结本周学习情况，突出关键进展。
2. **薄弱环节分析**：列出掌握程度最低的 2-3 个知识点，分析原因。
3. **下周学习建议**：给出 2-3 条具体可行的学习建议。

## 输出格式

```json
{
  "summary": "本周学习总结的 Markdown 文本",
  "weak_points": [{"point": "知识点名称", "accuracy": 0.33, "suggestion": "改进建议"}],
  "weekly_suggestion": "下周学习建议的 Markdown 文本"
}
```"""


def _get_week_data(week_start: str, week_end: str) -> dict:
    """汇总本周学习数据"""
    # 使用日期前缀匹配（兼容 ISO 格式字符串比较）
    end_prefix = week_end

    # 本周上传的资料
    new_docs = Document.query.filter(
        Document.created_at >= week_start,
        Document.created_at <= end_prefix + 'T99:99:99',
    ).count()

    # 本周提交的测评（排除 submitted_at 为 NULL 的历史记录）
    quizzes = Quiz.query.filter(
        Quiz.submitted_at >= week_start,
        Quiz.submitted_at <= end_prefix + 'T99:99:99',
        Quiz.submitted_at.isnot(None),
        Quiz.status == 'submitted',
    ).all()

    quiz_count = len(quizzes)
    avg_score = (
        sum(q.total_score for q in quizzes if q.total_score) / quiz_count
        if quiz_count > 0 else 0
    )

    # 薄弱知识点
    weak_kps = KnowledgePoint.query.filter(
        KnowledgePoint.mastery_level < 0.6,
    ).order_by(KnowledgePoint.mastery_level).limit(5).all()

    # 估算学习时长（基于 chunk 数 × 平均阅读时间）
    total_docs = Document.query.filter(Document.status == 'ready').count()
    study_hours = round(total_docs * 0.5 + quiz_count * 0.3, 1)

    return {
        'new_documents': new_docs,
        'quiz_count': quiz_count,
        'avg_score': round(avg_score, 1),
        'accuracy_trend': '—',
        'weak_kps': weak_kps,
        'study_time_hours': study_hours,
    }


@report_bp.route('/report/generate', methods=['POST'])
def generate_report():
    """AI 生成学习周报"""
    data = request.get_json(silent=True) or {}
    week_start = data.get('week_start') or _this_monday()
    week_end = data.get('week_end') or _this_sunday()

    # 汇总数据
    week_data = _get_week_data(week_start, week_end)

    # 构建 AI prompt
    weak_info = ''
    for kp in week_data['weak_kps']:
        weak_info += f'- {kp.name}: 掌握度 {kp.mastery_level:.0%}，共 {kp.total_questions} 题对 {kp.correct_count} 题\n'

    context = f"""本周 ({week_start} ~ {week_end}) 学习数据：

- 新上传资料：{week_data['new_documents']} 份
- 完成测评：{week_data['quiz_count']} 次
- 平均分：{week_data['avg_score']}
- 估算学习时长：{week_data['study_time_hours']} 小时

薄弱知识点：
{weak_info if weak_info else '暂无薄弱知识点数据'}

请基于以上数据生成学习周报。"""

    # AI 生成
    try:
        content = chat_complete([
            {'role': 'system', 'content': REPORT_PROMPT},
            {'role': 'user', 'content': context},
        ], temperature=0.5, max_tokens=2048)

        # 提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        content_json = json.loads(json_match.group(0)) if json_match else {}

    except Exception as e:
        logger.error('周报生成失败: %s', e, exc_info=True)
        return json_response(code=9999, message=f'生成失败：{str(e)}', status=500)

    # 构建完整报告
    report_json = {
        'summary': content_json.get('summary', ''),
        'study_time_hours': week_data['study_time_hours'],
        'new_documents': week_data['new_documents'],
        'quiz_count': week_data['quiz_count'],
        'avg_score': week_data['avg_score'],
        'accuracy_trend': week_data['accuracy_trend'],
        'weak_points': content_json.get('weak_points', []),
        'weekly_suggestion': content_json.get('weekly_suggestion', ''),
    }

    # 保存
    # 检查是否已存在同周报告
    existing = WeeklyReportModel.query.filter_by(week_start=week_start, week_end=week_end).first()
    if existing:
        existing.content_json = json.dumps(report_json, ensure_ascii=False)
        report = existing
    else:
        report = WeeklyReportModel(
            id=generate_id('rpt_'),
            week_start=week_start,
            week_end=week_end,
            content_json=json.dumps(report_json, ensure_ascii=False),
        )
        db.session.add(report)
    db.session.commit()

    return json_response(code=0, data={
        'id': report.id,
        'week_start': week_start,
        'week_end': week_end,
        'content': report_json,
        'generated_at': report.generated_at,
    })


@report_bp.route('/report/list', methods=['GET'])
def list_reports():
    reports = WeeklyReportModel.query.order_by(WeeklyReportModel.generated_at.desc()).all()
    return json_response(code=0, data=[r.to_dict() for r in reports])


@report_bp.route('/report/<report_id>', methods=['GET'])
def get_report(report_id: str):
    report = WeeklyReportModel.query.get(report_id)
    if not report:
        return json_response(code=1002, message='报告不存在', status=404)

    content = json.loads(report.content_json) if report.content_json else {}
    return json_response(code=0, data={
        'id': report.id,
        'week_start': report.week_start,
        'week_end': report.week_end,
        'content': content,
        'generated_at': report.generated_at,
    })


@report_bp.route('/report/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """下载周报为 Markdown 文件"""
    from flask import Response

    report = WeeklyReportModel.query.get(report_id)
    if not report:
        return json_response(code=1002, message='报告不存在', status=404)

    content = json.loads(report.content_json) if report.content_json else {}
    weak_list = '\n'.join(
        f'- **{wp.get("point", "")}**（正确率 {wp.get("accuracy", 0) * 100:.0f}%）：{wp.get("suggestion", "")}'
        for wp in content.get('weak_points', [])
    )

    md = f"""# 学习周报

**时间范围：** {report.week_start} ~ {report.week_end}

---

## 学习概况

{content.get('summary', '暂无')}

## 关键数据

- 学习时长：{content.get('study_time_hours', 0)} 小时
- 新上传资料：{content.get('new_documents', 0)} 份
- 完成测评：{content.get('quiz_count', 0)} 次
- 平均分：{content.get('avg_score', 0)} 分
- 成绩趋势：{content.get('accuracy_trend', '—')}

## 薄弱环节

{weak_list if weak_list else '暂无薄弱知识点'}

## 下周建议

{content.get('weekly_suggestion', '暂无')}

---
*生成于 {report.generated_at}*
"""

    return Response(
        md,
        mimetype='text/markdown; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="学习周报_{report.week_start}_{report.week_end}.md"',
        },
    )


# ---- 系统设置 ----

@report_bp.route('/settings', methods=['GET'])
def get_settings():
    return json_response(code=0, data={
        'llm_provider': current_app.config.get('LLM_PROVIDER', ''),
        'llm_model': current_app.config.get('LLM_MODEL_NAME', ''),
        'embedding_model': current_app.config.get('EMBEDDING_MODEL_NAME', ''),
        'chunk_size': current_app.config.get('CHUNK_SIZE', 800),
        'chunk_overlap': current_app.config.get('CHUNK_OVERLAP', 100),
        'top_k_default': current_app.config.get('TOP_K_DEFAULT', 5),
    })


@report_bp.route('/settings', methods=['PUT'])
def update_settings():
    data = request.get_json(silent=True) or {}
    for key, value in data.items():
        setting = Setting.query.get(key)
        if setting:
            setting.value = str(value)
        else:
            db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()
    return get_settings()


# ---- 辅助 ----

def _this_monday() -> str:
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _this_sunday() -> str:
    today = datetime.now(timezone.utc).date()
    sunday = today + timedelta(days=6 - today.weekday())
    return sunday.isoformat()
