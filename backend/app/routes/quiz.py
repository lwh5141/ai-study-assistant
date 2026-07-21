"""测评路由 — AI 出题 + AI 改卷 + 历史/错题"""

import json
import logging
from flask import Blueprint, request
from ..extensions import db
from ..models.models import Quiz, QuizQuestion, QuizAnswer, Document, Chunk, KnowledgePoint, _now
from ..services.llm import chat_complete_json
from ..utils.helpers import generate_id, json_response

logger = logging.getLogger(__name__)

quiz_bp = Blueprint('quiz', __name__)

# ---- 提示词（来自需求文档 4.2 / 4.3） ----

QUIZ_GENERATOR_PROMPT = """你是一个严格的测评出题系统。你的任务是基于用户已有的学习资料内容，生成一套测试题，用于考查用户对知识点的掌握程度。

## 出题规则

1. **严格基于资料**：你所出的每一道题，其考查的知识点必须在学习资料中有明确出处。不得编造资料中不存在的内容，不得超纲。
2. **题型与数量**：
   - 选择题（choice）：4 个选项，只有 1 个正确答案。选项中必须有 3 个是合理的干扰项（来自同一知识点的常见误解或相近概念）。
   - 判断题（true_false）：给出一个陈述，判断正确（true）或错误（false）。错误陈述应将正确概念中的关键部分替换为易混淆的错误说法。
   - 简答题（short_answer）：要求用 50-200 字回答。考查对核心概念的理解，而非死记硬背。
   - 三种题型的比例默认为 判断题 : 选择题 : 简答题 = 1 : 2 : 1（约 25% 判断 + 50% 选择 + 25% 简答）。
3. **难度梯度**：
   - 约 40% 为基础题（直接考查定义、概念）
   - 约 40% 为理解题（需要理解和对比不同概念）
   - 约 20% 为应用题（需要结合实际场景分析）
4. **知识点覆盖**：优先覆盖资料中的核心知识点，避免多题考查同一知识点。
5. **质量控制**：
   - 每道题必须有标准答案
   - 每道题必须有答案解析
   - 每道题必须标注来源资料名称和页码

## 输出格式

以 JSON 数组格式输出，每题结构如下：
[{"type": "choice", "content": "题目", "options": [{"key": "A", "text": "选项A"}, ...], "correct_answer": "B", "explanation": "解析", "source_document": "资料名", "source_page": 页码}]"""


GRADER_PROMPT = """你是一个公正严格的判分系统。你的任务是对用户的测评答案进行评分，并给出建设性反馈。

## 判分规则

### 选择题（choice）
- 用户答案与标准答案完全一致 → 1 分，标记为正确
- 不一致 → 0 分，标记为错误

### 判断题（true_false）
- 用户答案与标准答案一致 → 1 分，标记为正确
- 不一致 → 0 分，标记为错误

### 简答题（short_answer）
三档评分：
- 1.0 分：回答准确、完整，包含核心要点，表述清晰
- 0.5 分：触及部分核心要点，但不够完整或有轻微偏差
- 0 分：完全偏离核心要点或答非所问
评分时提供简短评语（1-2 句）。

## 输出格式

{"results": [{"question_id": "q_001", "is_correct": true, "score": 1.0, "comment": ""}]}

如果用户未作答（答案为空或"不会"），直接判 0 分，评语为"未作答"。"""


def _gather_chunks(document_ids: list[str] | None = None, max_chunks: int = 40) -> list[dict]:
    """收集资料文本块作为 AI 上下文"""
    query = Chunk.query
    if document_ids:
        query = query.filter(Chunk.document_id.in_(document_ids))
    chunks = query.limit(max_chunks).all()

    result = []
    for c in chunks:
        doc = Document.query.get(c.document_id)
        doc_name = doc.filename if doc else 'unknown'
        result.append({
            'document_name': doc_name,
            'page_number': c.page_number or 0,
            'content': c.content,
        })
    return result


# ---- 生成测评 ----

@quiz_bp.route('/quiz/generate', methods=['POST'])
def generate_quiz():
    """AI 自动出题"""
    data = request.get_json(silent=True) or {}
    question_count = data.get('question_count', 10)
    document_ids = data.get('document_ids')
    title = data.get('title', '')

    # 收集资料内容
    chunks = _gather_chunks(document_ids)
    if not chunks:
        return json_response(code=1005, message='无可用资料，请先上传并解析学习资料', status=422)

    # 构建资料摘要
    context_parts = []
    for c in chunks[:30]:
        context_parts.append(f"【《{c['document_name']}》第{c['page_number']}页】\n{c['content'][:500]}")
    context = '\n\n'.join(context_parts)

    # 调用 AI 出题
    try:
        questions = chat_complete_json([
            {'role': 'system', 'content': QUIZ_GENERATOR_PROMPT},
            {'role': 'user', 'content': f'请基于以下资料生成 {question_count} 道测试题：\n\n{context}'},
        ], temperature=0.7, max_tokens=8192)

        if not isinstance(questions, list):
            questions = questions.get('questions', []) if isinstance(questions, dict) else []

    except Exception as e:
        logger.error('出题失败: %s', e, exc_info=True)
        return json_response(code=9999, message=f'出题失败：{str(e)}', status=500)

    if not questions:
        return json_response(code=1005, message='资料内容不足以生成题目', status=422)

    # 保存到数据库
    quiz = Quiz(
        id=generate_id('quiz_'),
        title=title or f'AI 测评 ({len(questions)}题)',
        question_count=len(questions),
        document_ids=json.dumps(document_ids) if document_ids else '[]',
        status='ready',
    )
    db.session.add(quiz)

    quiz_questions = []
    for i, q in enumerate(questions):
        q_type = q.get('type', 'choice')
        qq = QuizQuestion(
            id=generate_id('q_'),
            quiz_id=quiz.id,
            question_index=i + 1,
            type=q_type,
            content=q.get('content', ''),
            options=json.dumps(q.get('options', []), ensure_ascii=False),
            correct_answer=str(q.get('correct_answer', '')),
            explanation=q.get('explanation', ''),
            source_document_id=q.get('source_document', ''),
            source_page=q.get('source_page'),
        )
        db.session.add(qq)
        quiz_questions.append(qq)

    db.session.commit()

    # 返回时不含答案（前端防护）
    return json_response(code=0, data={
        'quiz_id': quiz.id,
        'title': quiz.title,
        'question_count': quiz.question_count,
        'status': 'ready',
        'questions': [qq.to_dict(include_answer=False) for qq in quiz_questions],
        'created_at': quiz.created_at,
    }, status=201)


# ---- 提交测评 ----

@quiz_bp.route('/quiz/<quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id: str):
    """提交答案 + AI 改卷"""
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return json_response(code=1002, message='测评不存在', status=404)
    if quiz.status == 'submitted':
        return json_response(code=1003, message='测评已提交过', status=409)

    data = request.get_json(silent=True) or {}
    answers = data.get('answers', [])

    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).order_by(QuizQuestion.question_index).all()

    # 构建改卷 prompt
    q_list = []
    for q in questions:
        user_answer = next((a.get('answer', '') for a in answers if a.get('question_id') == q.id), '')
        q_list.append({
            'question_id': q.id,
            'type': q.type,
            'content': q.content,
            'correct_answer': q.correct_answer,
            'user_answer': user_answer or '',
            'options': q.options,
        })

    # AI 判分
    try:
        grader_input = f'请批改以下测评：\n{json.dumps(q_list, ensure_ascii=False, indent=2)}'
        result = chat_complete_json([
            {'role': 'system', 'content': GRADER_PROMPT},
            {'role': 'user', 'content': grader_input},
        ], temperature=0.1, max_tokens=4096)

        grading = result.get('results', []) if isinstance(result, dict) else result
    except Exception as e:
        logger.error('改卷失败: %s', e, exc_info=True)
        return json_response(code=9999, message=f'改卷失败：{str(e)}', status=500)

    # 保存答案 + 计算总分
    total_score = 0
    correct_count = 0
    details = []

    for q in questions:
        grade = next((g for g in grading if g.get('question_id') == q.id), None)
        user_answer = next((a.get('answer', '') for a in answers if a.get('question_id') == q.id), '')

        is_correct = grade.get('is_correct', False) if grade else False
        score = grade.get('score', 1.0 if is_correct else 0.0) if grade else 0.0
        comment = grade.get('comment', '') if grade else ''

        answer_record = QuizAnswer(
            id=generate_id('ans_'),
            quiz_id=quiz_id,
            question_id=q.id,
            user_answer=user_answer or '',
            is_correct=is_correct,
            score=score,
        )
        db.session.add(answer_record)

        if is_correct:
            correct_count += 1
        total_score += score

        details.append({
            'question_id': q.id,
            'index': q.question_index,
            'type': q.type,
            'content': q.content,
            'user_answer': user_answer or '',
            'correct_answer': q.correct_answer,
            'is_correct': is_correct,
            'score': score,
            'explanation': q.explanation or comment,
            'source_document': q.source_document_id,
            'source_page': q.source_page,
        })

    # 更新测评状态
    scaled_score = round((total_score / len(questions)) * 100)
    quiz.status = 'submitted'
    quiz.total_score = scaled_score
    quiz.correct_count = correct_count
    quiz.submitted_at = _now()
    db.session.commit()

    # 更新知识点掌握度（失败不影响提交流程）
    try:
        _update_knowledge_points(quiz_id, questions, details)
    except Exception as e:
        logger.warning('知识点更新失败: %s', e)

    return json_response(code=0, data={
        'quiz_id': quiz_id,
        'total_score': scaled_score,
        'correct_count': correct_count,
        'total_count': len(questions),
        'accuracy': round(correct_count / len(questions), 2),
        'details': details,
        'weak_points': _compute_weak_points(questions, details),
        'submitted_at': quiz.submitted_at,
    })


# ---- 结果 / 历史 / 错题 ----

@quiz_bp.route('/quiz/<quiz_id>/result', methods=['GET'])
def get_quiz_result(quiz_id: str):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return json_response(code=1002, message='测评不存在', status=404)
    if quiz.status != 'submitted':
        return json_response(code=1005, message='尚未提交', status=422)

    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).order_by(QuizQuestion.question_index).all()
    answers = {a.question_id: a for a in QuizAnswer.query.filter_by(quiz_id=quiz_id).all()}

    details = []
    for q in questions:
        a = answers.get(q.id)
        details.append({
            'question_id': q.id,
            'index': q.question_index,
            'type': q.type,
            'content': q.content,
            'user_answer': a.user_answer if a else '',
            'correct_answer': q.correct_answer,
            'is_correct': a.is_correct if a else False,
            'score': a.score if a else 0.0,
            'explanation': q.explanation or '',
            'source_document': q.source_document_id,
            'source_page': q.source_page,
        })

    return json_response(code=0, data={
        'quiz_id': quiz_id,
        'total_score': quiz.total_score,
        'correct_count': quiz.correct_count,
        'total_count': quiz.question_count,
        'accuracy': round(quiz.correct_count / quiz.question_count, 2) if quiz.correct_count is not None else 0,
        'details': details,
        'weak_points': _compute_weak_points(questions, details),
        'submitted_at': quiz.submitted_at,
    })


@quiz_bp.route('/quiz/history', methods=['GET'])
def get_quiz_history():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)

    pagination = Quiz.query.order_by(Quiz.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False,
    )
    return json_response(code=0, data={
        'total': pagination.total,
        'items': [q.to_dict() for q in pagination.items],
    })


@quiz_bp.route('/quiz/wrong-questions', methods=['GET'])
def get_wrong_questions():
    page = request.args.get('page', 1, type=int)
    document_id = request.args.get('document_id', '')

    query = QuizAnswer.query.filter_by(is_correct=False)
    if document_id:
        # 通过 question → quiz → document_ids 关联
        q_ids = [q.id for q in QuizQuestion.query.filter(
            QuizQuestion.quiz_id.in_(
                db.session.query(Quiz.id).filter(Quiz.document_ids.contains(document_id))
            )
        ).all()]
        query = query.filter(QuizAnswer.question_id.in_(q_ids))

    pagination = query.paginate(page=page, per_page=20, error_out=False)

    items = []
    for a in pagination.items:
        q = QuizQuestion.query.get(a.question_id)
        if q:
            items.append({
                'question_id': q.id,
                'quiz_id': a.quiz_id,
                'type': q.type,
                'content': q.content,
                'user_answer': a.user_answer,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation or '',
                'source_document': q.source_document_id,
                'created_at': a.submitted_at or q.created_at,
            })

    return json_response(code=0, data={'total': pagination.total, 'items': items})


# ---- 删除测评 ----

@quiz_bp.route('/quiz/<quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id: str):
    """删除单条测评记录。

    - 级联删除 Quiz + QuizQuestion + QuizAnswer（模型层已配置 cascade）
    - 若 quiz 已提交，先回退知识点统计（total_questions / correct_count / mastery_level）
    """
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return json_response(code=1002, message='测评不存在', status=404)

    # 已提交的测评需要回退知识点统计
    if quiz.status == 'submitted':
        try:
            _revert_knowledge_points(quiz_id)
        except Exception as e:
            # 回退失败不阻断删除，但记录日志
            logger.warning('知识点回退失败 (quiz=%s): %s', quiz_id, e)

    deleted_title = quiz.title
    deleted_status = quiz.status

    db.session.delete(quiz)
    db.session.commit()

    return json_response(code=0, data={
        'deleted': quiz_id,
        'title': deleted_title,
        'status': deleted_status,
    })


@quiz_bp.route('/quiz', methods=['DELETE'])
def clear_quizzes():
    """清空全部测评记录。

    查询参数:
    - status: 可选，过滤状态（ready / submitted）。不传则删除全部

    性能优化：使用 _revert_knowledge_points_batch 批量回退，避免 N 次循环查询。
    """
    status = request.args.get('status')
    query = Quiz.query
    if status:
        query = query.filter_by(status=status)

    quizzes = query.all()

    # 批量回退所有已提交 quiz 的知识点统计（一次性查询，内存聚合）
    submitted_ids = [q.id for q in quizzes if q.status == 'submitted']
    if submitted_ids:
        try:
            _revert_knowledge_points_batch(submitted_ids)
        except Exception as e:
            logger.warning('批量知识点回退失败 (%d quizzes): %s', len(submitted_ids), e)

    for q in quizzes:
        db.session.delete(q)
    db.session.commit()

    return json_response(code=0, data={
        'deleted_count': len(quizzes),
    })


# ---- 辅助函数 ----

def _revert_knowledge_points(quiz_id: str):
    """删除已提交测评前，回退相关知识点统计（单条场景）。

    KnowledgePoint 与 Quiz 无外键关联，需通过 QuizQuestion.content[:50] + source_document_id 反查。
    使用 max(0, ...) 防止负数；total_questions=0 时 mastery=0.0。
    回退后若该知识点已无任何答题记录（total=0），删除该 KnowledgePoint 避免残留垃圾数据。
    """
    answers = QuizAnswer.query.filter_by(quiz_id=quiz_id).all()
    to_delete = []  # 收集回退后 total=0 的知识点
    for a in answers:
        q = QuizQuestion.query.get(a.question_id)
        if not q:
            continue
        kp_name = q.content[:50]
        kp = KnowledgePoint.query.filter_by(
            name=kp_name, document_id=q.source_document_id or ''
        ).first()
        if not kp:
            continue

        kp.total_questions = max(0, kp.total_questions - 1)
        if a.is_correct:
            kp.correct_count = max(0, kp.correct_count - 1)
        kp.mastery_level = (
            kp.correct_count / kp.total_questions
            if kp.total_questions > 0
            else 0.0
        )
        # 回退后已无任何答题记录 → 标记删除
        if kp.total_questions == 0:
            to_delete.append(kp)

    for kp in to_delete:
        db.session.delete(kp)
    db.session.flush()


def _revert_knowledge_points_batch(quiz_ids: list[str]):
    """批量回退知识点统计（清空全部场景，性能优化版）。

    与单条版本的区别：
    - 一次性查询所有 QuizAnswer + QuizQuestion，避免 N 次循环查询
    - 在内存中按 (name, document_id) 聚合扣减量，最后批量更新
    - 同样处理 total=0 的残留记录删除

    适用于一次删除多个 quiz 的场景（如 clear_quizzes 端点）。
    """
    if not quiz_ids:
        return

    # 一次性查所有 answers 和 questions
    answers = QuizAnswer.query.filter(QuizAnswer.quiz_id.in_(quiz_ids)).all()
    if not answers:
        return

    question_ids = [a.question_id for a in answers]
    questions = {
        q.id: q
        for q in QuizQuestion.query.filter(QuizQuestion.id.in_(question_ids)).all()
    }

    # 按 (kp_name, document_id) 聚合扣减量
    # key: "name::document_id" → {kp, deduct_total, deduct_correct}
    stats: dict[str, dict] = {}

    for a in answers:
        q = questions.get(a.question_id)
        if not q:
            continue
        kp_name = q.content[:50]
        doc_id = q.source_document_id or ''
        key = f'{kp_name}::{doc_id}'

        if key not in stats:
            kp = KnowledgePoint.query.filter_by(name=kp_name, document_id=doc_id).first()
            if not kp:
                continue
            stats[key] = {'kp': kp, 'deduct_total': 0, 'deduct_correct': 0}

        stats[key]['deduct_total'] += 1
        if a.is_correct:
            stats[key]['deduct_correct'] += 1

    # 批量更新 + 收集待删除
    to_delete = []
    for entry in stats.values():
        kp = entry['kp']
        kp.total_questions = max(0, kp.total_questions - entry['deduct_total'])
        kp.correct_count = max(0, kp.correct_count - entry['deduct_correct'])
        kp.mastery_level = (
            kp.correct_count / kp.total_questions
            if kp.total_questions > 0
            else 0.0
        )
        if kp.total_questions == 0:
            to_delete.append(kp)

    for kp in to_delete:
        db.session.delete(kp)
    db.session.flush()


# ---- 辅助函数 ----

def _compute_weak_points(questions: list[QuizQuestion], details: list[dict]) -> list[dict]:
    """从结果中提取薄弱知识点"""
    errors: dict[str, dict] = {}
    for i, q in enumerate(questions):
        detail = details[i] if i < len(details) else {}
        if not detail.get('is_correct', False):
            # 用前 60 字做去重键，完整题目做展示文本
            dedup_key = q.content[:60]
            if dedup_key not in errors:
                errors[dedup_key] = {
                    'knowledge_point': q.content,   # 完整题目内容
                    'document': q.source_document_id or '',
                    'error_count': 0,
                }
            errors[dedup_key]['error_count'] += 1
    return list(errors.values())[:5]


def _update_knowledge_points(quiz_id: str, questions: list[QuizQuestion], details: list[dict]):
    """更新知识点掌握度"""
    for i, q in enumerate(questions):
        detail = details[i] if i < len(details) else {}
        source_doc = q.source_document_id or ''
        kp_name = q.content[:50]

        kp = KnowledgePoint.query.filter_by(name=kp_name, document_id=source_doc).first()
        if not kp:
            kp = KnowledgePoint(
                id=generate_id('kp_'),
                name=kp_name,
                document_id=source_doc,
                total_questions=0,
                correct_count=0,
                mastery_level=0.0,
            )
            db.session.add(kp)

        kp.total_questions += 1
        if detail.get('is_correct', False):
            kp.correct_count += 1
        kp.mastery_level = kp.correct_count / kp.total_questions if kp.total_questions > 0 else 0.0

    db.session.commit()
