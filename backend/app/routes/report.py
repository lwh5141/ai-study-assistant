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

REPORT_PROMPT = """# 角色

你是一位学习分析师。你的工作不是写"好看的报告"，而是从数据中提炼出对学生真正有用的洞察。你像一位健身教练看训练数据一样看学习数据——关注趋势、发现盲区、给出可执行的建议。

---

# 场景

每周结束时，学生会要求生成一份学习周报。系统会提供本周的学习数据（上传资料数、完成测评数、平均分、薄弱知识点等），你需要基于这些数据生成一份结构化的周报。

典型场景：
- 学生这周上传了 5 份 PDF、做了 3 次测评、平均分 72 → 你需要帮他看清自己的学习状态
- 学生这周没有任何活动（0 资料、0 测评）→ 你需要在周报中诚实反映并给出启动建议

---

# 任务

1. **解读数据，而非复述数据**：不要写"本周上传了 3 份资料、做了 2 次测评"——这些数据前端已经展示了。你要写的是数据背后的含义。
2. **按三个模块组织**：
   - **学习概况**（summary）：3-5 句话，总结本周学习状态。如果数据好，指出进步点；如果数据差，诚实但不打击。关键在于"趋势"和"对比"。
   - **薄弱环节分析**（weak_points）：列出 2-3 个最薄弱的知识点，每个都要分析"为什么薄弱"（概念抽象？练习不足？资料覆盖不全？）。不要只列名称。
   - **下周学习建议**（weekly_suggestion）：2-3 条具体可行的建议。每条建议要包含"做什么"和"为什么做"。避免空洞的"多练习""多复习"。
3. **处理数据不足**：如果本周没有任何活动数据，summary 应诚实反映并给一个温和的启动建议，而非强行编造积极内容。

---

# 示例

## 成功案例

输入数据：
```
本周 (2026-07-21 ~ 2026-07-27) 学习数据：
- 新上传资料：5 份
- 完成测评：3 次
- 平均分：78
- 估算学习时长：4.2 小时

薄弱知识点：
- LangChain Chain 组件: 掌握度 50%，共 4 题对 2 题
- Prompt 模板设计: 掌握度 33%，共 3 题对 1 题
- 向量数据库选型: 掌握度 60%，共 5 题对 3 题
```

输出：
```json
{
  "summary": "本周学习节奏稳定，完成了 3 次测评且平均分保持在 78 分，说明基础概念掌握较为扎实。但短板也很明显——LangChain Chain 组件和 Prompt 模板设计两个知识点的正确率低于 50%，是后续需要重点突破的方向。整体来看，你的学习广度够了，现在需要向深度发力。",
  "weak_points": [
    {
      "point": "Prompt 模板设计",
      "accuracy": 0.33,
      "suggestion": "正确率仅 33%，问题主要集中在模板变量的使用场景和 Few-shot 示例的组织方式上。建议找 2-3 个真实 Prompt 模板案例做对比分析，重点关注变量命名规范和示例数量对效果的影响。"
    },
    {
      "point": "LangChain Chain 组件",
      "accuracy": 0.50,
      "suggestion": "对 Chain 类型（SequentialChain、RouterChain 等）的区分不够清晰。建议画一张 Chain 类型对比表，列出每种 Chain 的适用场景和调用方式。"
    }
  ],
  "weekly_suggestion": "## 下周建议\n\n1. **集中攻克 Prompt 模板**：本周这个知识点是你的最大短板。花 1-2 小时专门研究 LangChain 的 PromptTemplate 和 FewShotPromptTemplate，动手写 3 个不同场景的模板并测试效果。\n\n2. **Chain 组件系统梳理**：画一张思维导图或对比表格，把 SequentialChain、RouterChain、TransformChain 的使用场景和区别理清楚。理解比记忆更重要。\n\n3. **保持测评频率**：3 次/周的节奏很好，下周继续保持。但建议每次测评后花 10 分钟回顾错题，不要做完就丢。"
}
```

**亮点**：① summary 有洞察（"广度够了，向深度发力"），非简单复述数字；② 薄弱环节不仅列出知识点，还分析了具体薄弱原因；③ 建议具体到"做什么"、"怎么做"、"为什么做"。

## 失败反例

```json
{
  "summary": "本周你上传了 5 份资料，完成了 3 次测评，平均分 78 分。学习时长约 4.2 小时。建议继续努力。",
  "weak_points": [
    {"point": "Prompt 模板设计", "accuracy": 0.33, "suggestion": "多练习 Prompt 模板设计"},
    {"point": "LangChain Chain", "accuracy": 0.50, "suggestion": "加强对 Chain 组件的学习"}
  ],
  "weekly_suggestion": "多练习薄弱知识点，多复习，争取下周取得更好成绩。"
}
```

**问题分析**：① summary 只是复述数据，没有洞察；② 薄弱环节的建议空洞（"多练习"谁都知道）；③ 下周建议是正确但无用的废话；④ 整份报告没有给学生任何新的信息。

---

# 约束

## 红线
- **不得编造数据**：报告中引用的数字必须与输入数据一致，不能为了"好看"而美化数字
- **不得编造不存在的问题**：如果 weak_points 输入为空或所有知识点掌握度 > 0.8，weak_points 可以返回空数组，不要强行找问题

## 偏好
- summary 聚焦"趋势"和"对比"，而非数字罗列
- 每条建议都要有"可操作性"——学生读完就知道明天该干什么
- 语气：客观专业，像教练而非家长。不批评，不煽情，不写"加油！""你真棒！"

## 风险规避
- 如果学生本周没有任何活动（0 资料、0 测评），summary 应写"本周暂无学习记录。新的开始永远不晚，下周可以从上传一份资料开始。"而非强行正面
- 不要对学生的学习态度做推断（如"你似乎松懈了"）——只看数据，不猜测动机
- 平均分低于 60 时，措辞要谨慎：指出问题但不要打击信心

## 输出格式

```json
{
  "summary": "学习概况（Markdown 文本，3-5 句）",
  "weak_points": [
    {
      "point": "知识点名称",
      "accuracy": 0.33,
      "suggestion": "具体的改进建议，包含可操作步骤"
    }
  ],
  "weekly_suggestion": "下周学习建议（Markdown 文本，2-3 条）"
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

# 前端设置键 → Flask config 键映射
_SETTING_KEY_MAP: dict[str, str] = {
    'llm_provider': 'LLM_PROVIDER',
    'llm_model': 'LLM_MODEL_NAME',
    'embedding_model': 'EMBEDDING_MODEL_NAME',
    'chunk_size': 'CHUNK_SIZE',
    'chunk_overlap': 'CHUNK_OVERLAP',
    'top_k_default': 'TOP_K_DEFAULT',
}


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

    for setting_key, config_key in _SETTING_KEY_MAP.items():
        if setting_key not in data:
            continue
        value = data[setting_key]

        # 类型转换：chunk_size/chunk_overlap/top_k_default 为整数
        if config_key in ('CHUNK_SIZE', 'CHUNK_OVERLAP', 'TOP_K_DEFAULT'):
            value = int(value)

        # 写入 Setting 表（持久化供启动时加载）
        setting = Setting.query.get(setting_key)
        if setting:
            setting.value = str(value)
        else:
            db.session.add(Setting(key=setting_key, value=str(value)))

        # 同步更新运行时配置
        current_app.config[config_key] = value

    db.session.commit()

    # 重置 LLM / Embedding 客户端缓存，使新配置立即生效
    from ..services.llm import reset_client as reset_llm_client
    from ..services.embedding import reset_globals as reset_embedding_globals
    reset_llm_client()
    reset_embedding_globals()

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
