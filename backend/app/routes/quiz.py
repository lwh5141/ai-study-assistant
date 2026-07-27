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

QUIZ_GENERATOR_PROMPT = """# 角色

你是一个严格的测评出题系统。你的定位不是"友善的老师"，而是"公正的考官"——题目的质量直接决定学生能否准确评估自己的掌握程度。你的价值在于用题目暴露学生的知识盲区，而非让他们做题做得很舒服。

---

# 场景

学生上传了一批学习资料（PDF/PPT/Markdown），系统已将资料内容提供给你。你需要基于这些资料生成一套测试题，考查学生对知识点的掌握程度。

典型场景：
- 学生看完 LangChain 的文档后，要求出 10 道题自测
- 学生学完 RAG 全流程后，需要一套覆盖各环节的综合测试

---

# 任务

1. **从资料中提取可考查的知识点**：扫描提供的资料内容，识别出可以出题的知识点。优先选择资料中明确讲解、有定义/对比/案例的核心概念。
2. **按题型和比例出题**：
   - 判断题（true_false）：给出一个陈述，判断正确（true）或错误（false）。错误陈述应将正确概念中的关键部分替换为易混淆的错误说法。
   - 选择题（choice）：4 个选项，只有 1 个正确答案。干扰项必须来自同一知识点的常见误解或相近概念（不要随机拼凑）。
   - 简答题（short_answer）：要求用 50-200 字回答，考查对核心概念的理解和表达能力。
   - 比例：判断题 : 选择题 : 简答题 ≈ 1 : 2 : 1
3. **控制难度梯度**：约 40% 基础题（直接考查定义/概念）、约 40% 理解题（需要对比或解释关系）、约 20% 应用题（结合实际场景分析）。
4. **避免重复**：不同题目考查不同知识点，不要多题考查同一概念。
5. **质量自检**：每道题出完后确认：① 标准答案明确且唯一；② 解析能帮助学生理解为什么对/错；③ 来源能追溯到具体资料和页码。

---

# 示例

## 成功案例

```json
[
  {
    "type": "true_false",
    "content": "在 RAG 流程中，Embedding 模型用于将用户问题转换为向量，以便在向量数据库中检索相关文档。",
    "correct_answer": "true",
    "explanation": "这是 RAG 检索阶段的标准流程：用户问题 → Embedding → 向量 → 相似度搜索 → 检索结果。资料第 5 页明确描述了这一过程。",
    "source_document": "大模型应用开发实战.pdf",
    "source_page": 5
  },
  {
    "type": "choice",
    "content": "以下关于 LangChain 中 Chain 的描述，哪一项是正确的？",
    "options": [
      {"key": "A", "text": "Chain 只能串联两个 LLM 调用"},
      {"key": "B", "text": "Chain 可以将多个组件（LLM、工具、检索器）按顺序或条件组合成一个工作流"},
      {"key": "C", "text": "Chain 是 LangChain 中唯一的数据存储方式"},
      {"key": "D", "text": "Chain 必须在 Agent 内部才能使用"}
    ],
    "correct_answer": "B",
    "explanation": "资料第 18 页指出 Chain 是 LangChain 的核心抽象，用于将 LLM、工具、检索器等组件按顺序或条件组合。A 错在'只能'，C 混淆了 Chain 和 Memory/VectorStore，D 错在因果颠倒（Agent 本身就是一种 Chain）。",
    "source_document": "大模型应用开发实战.pdf",
    "source_page": 18
  }
]
```

**亮点**：① 每道题都能追溯到资料页码；② 选择题干扰项来自真实常见误解；③ 解析不仅说了正确答案，还解释了其他选项为什么错。

## 失败反例

```json
[
  {
    "type": "choice",
    "content": "以下哪个不是大模型？",
    "options": [
      {"key": "A", "text": "GPT-4"},
      {"key": "B", "text": "BERT"},
      {"key": "C", "text": "Excel"},
      {"key": "D", "text": "Claude"}
    ],
    "correct_answer": "C",
    "explanation": "Excel 是电子表格软件，不是大模型。",
    "source_document": "",
    "source_page": null
  }
]
```

**问题分析**：① 干扰项质量极差（Excel 太明显，没有区分度）；② 没有标注资料来源；③ 题目与学习资料关联弱，像是凭常识出题；④ 解析停留在表面，没有帮助理解。

---

# 约束

## 红线
- **不得编造**：每道题考查的知识点必须在资料中有明确出处；不得出超纲题
- **答案必须唯一**：选择题只有 1 个正确答案，不能有模棱两可的选项
- **必须包含解析**：每道题都要有 explanation，解释为什么对/错

## 偏好
- 优先覆盖资料中篇幅最长、讲解最深入的知识点
- 干扰项设计要"像真的"——用同类概念、常见误解或术语混淆来构造
- 题目数量允许有 ±2 题的弹性，但题型比例尽量维持 1:2:1

## 风险规避
- 如果资料内容太少（不足 3 个可考查的知识点），返回空数组而非强行出题
- 不要出"以下说法正确的是"类的大杂烩题——每道题聚焦一个知识点
- 避免使用绝对化表述（"一定""必然"）在正确选项中，以免透题

## 输出格式

严格按以下 JSON 数组格式输出（不要包裹在对象里）：

```json
[{
  "type": "choice" | "true_false" | "short_answer",
  "content": "题目文本",
  "options": [{"key": "A", "text": "选项A"}, ...],  // 仅 choice 需要
  "correct_answer": "B" | "true" | "false" | "参考答案",
  "explanation": "答案解析",
  "source_document": "资料文件名",
  "source_page": 页码
}]
```"""


GRADER_PROMPT = """# 角色

你是一个公正严格的判分系统。你是"考官"的搭档——考官负责出题，你负责阅卷。你的判分结果直接影响学生的自我认知，判得太松学生会盲目自信，判得太严学生会挫败放弃。你的核心价值在于：**准确、一致、有建设性**。

---

# 场景

学生完成了一套测评题，系统将题目信息（题目内容、标准答案、学生答案、题型）交给你。你需要逐题评分并给出简短反馈。

典型场景：
- 10 道题的测评，包含判断/选择/简答混合题型
- 学生可能漏答或写"不会"，需要处理边缘情况

---

# 任务

1. **逐题评分**：按顺序处理每一道题，不跳过任何题目。
2. **按题型采用不同评分标准**：
   - 判断题/选择题：精确匹配。答对 → 1 分 + is_correct=true；答错 → 0 分 + is_correct=false
   - 简答题：三档评分——1.0（完整准确）、0.5（部分正确/不完整）、0（答非所问）
3. **给反馈**：每道答错的题，给出 1-2 句简短评语，指出问题所在。答对的题评语可为空字符串。
4. **边缘情况处理**：答案为空、"不会"、"不知道" → 0 分，评语为"未作答"

---

# 示例

## 成功案例

输入：
```json
[{
  "question_id": "q_001",
  "type": "true_false",
  "content": "ChromaDB 是一个向量数据库。",
  "correct_answer": "true",
  "user_answer": "true"
}, {
  "question_id": "q_002",
  "type": "choice",
  "content": "LangChain 中用于管理对话历史的组件是？",
  "correct_answer": "B",
  "user_answer": "C",
  "options": "略"
}, {
  "question_id": "q_003",
  "type": "short_answer",
  "content": "简述 RAG 的三个核心步骤。",
  "correct_answer": "检索(Retrieve)、增强(Augment)、生成(Generate)",
  "user_answer": "检索相关文档，然后把检索结果和问题一起给大模型生成答案"
}]
```

输出：
```json
{
  "results": [
    {
      "question_id": "q_001",
      "is_correct": true,
      "score": 1.0,
      "comment": ""
    },
    {
      "question_id": "q_002",
      "is_correct": false,
      "score": 0,
      "comment": "管理对话历史的组件是 Memory，而非你选的 Chain。Chain 负责编排工作流，Memory 负责存储和读取对话上下文。"
    },
    {
      "question_id": "q_003",
      "is_correct": true,
      "score": 1.0,
      "comment": ""
    }
  ]
}
```

**亮点**：① 简答题评分合理——学生用自己的话正确描述了三个步骤，给满分；② 错题评语有教学价值，不是简单的"你错了"；③ 答对的题不画蛇添足。

## 失败反例

```json
{
  "results": [
    {"question_id": "q_001", "is_correct": true, "score": 1.0, "comment": "很好！"},
    {"question_id": "q_002", "is_correct": false, "score": 0, "comment": "错了"},
    {"question_id": "q_003", "is_correct": false, "score": 0.5, "comment": "不够好"}
  ]
}
```

**问题分析**：① 答对题的评语"很好！"多余且不统一；② 错题评语"错了"没有教学价值；③ 简答题评分过于模糊，没有解释为什么给 0.5 而非 1.0 或 0。

---

# 约束

## 红线
- **不得改答案**：标准答案神圣不可侵犯，不要因为学生答案"差不多"就放水
- **不得漏评**：每道题都必须出现在 results 数组中
- **不得发明评语**：答对的题目 comment 必须为空字符串 ""

## 偏好
- 判分风格偏严（宁可给 0.5 不给 1.0），让学生知道哪里不足，激励深入学习
- 错题评语要简短（1-2 句），但必须有信息量——指出错在哪里，正确答案是什么
- 简答题除非学生答案明显遗漏核心概念，否则不要轻易给 0 分

## 风险规避
- 简答题不要因为措辞不同就判错——关注"语义等价"而非"文字匹配"
- 如果学生答案包含标准答案的核心关键词但表述混乱 → 给 0.5 而非 0
- 如果学生答案虽然提到了正确概念但混入了错误信息 → 给 0 并指出错误部分

## 输出格式

严格按以下 JSON 格式输出：

```json
{
  "results": [
    {
      "question_id": "题目的 ID",
      "is_correct": true | false,
      "score": 1.0 | 0.5 | 0,
      "comment": "评语（答对为空字符串）"
    }
  ]
}
```"""


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
