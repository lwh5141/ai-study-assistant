// ============================================================
// API 请求/响应 TypeScript 类型定义
// 依据：docs/requirements.md 后台接口设计
// ============================================================

// ---- 通用结构 ----

export interface ApiResponse<T> {
  code: number
  data: T
}

export interface ApiError {
  code: number
  message: string
  status: number
}

export interface PaginatedData<T> {
  total: number
  items: T[]
}

// ---- 资料 (Documents) ----

export type DocumentStatus = 'processing' | 'ready' | 'error'
export type FileType = 'pdf' | 'ppt' | 'pptx' | 'md' | 'doc' | 'docx' | 'txt'

export interface Document {
  id: string
  filename: string
  file_type: FileType
  file_size: number
  status: DocumentStatus
  chunk_count: number
  created_at: string
  updated_at?: string
  error_message?: string
}

export interface UploadResponse {
  id: string
  filename: string
  file_type: FileType
  file_size: number
  status: DocumentStatus
  chunk_count: number
  created_at: string
}

export interface DeleteDocumentResponse {
  message: string
}

// ---- 对话 (Chat) ----

export interface ChatSource {
  document_id: string
  document_name: string
  page: number
  chunk_index: number
  excerpt: string
  relevance_score: number
}

export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  created_at: string
}

export interface ChatSession {
  session_id: string
  title: string
  document_ids: string[]
  message_count: number
  preview: string
  created_at: string
  updated_at: string
}

export interface ChatSessionDetail {
  session_id: string
  title: string
  document_ids: string[]
  messages: ChatMessage[]
}

export interface SendMessageRequest {
  session_id?: string
  message: string
  document_ids?: string[]
  top_k?: number
}

export interface SendMessageResponse {
  session_id: string
  message_id: string
  role: 'assistant'
  content: string
  sources: ChatSource[]
  created_at: string
}

// ---- 测评 (Quiz) ----

export type QuestionType = 'choice' | 'true_false' | 'short_answer'
export type QuizStatus = 'ready' | 'submitted'

export interface QuizOption {
  key: string
  text: string
}

export interface QuizQuestion {
  question_id: string
  index: number
  type: QuestionType
  content: string
  options?: QuizOption[]
  correct_answer?: string
  explanation?: string
  source_document?: string
  source_page?: number
}

export interface Quiz {
  quiz_id: string
  title: string
  question_count: number
  status: QuizStatus
  questions: QuizQuestion[]
  created_at: string
}

export interface GenerateQuizRequest {
  title?: string
  question_count?: number
  document_ids?: string[]
  question_types?: QuestionType[]
}

export interface QuizAnswer {
  question_id: string
  answer: string
}

export interface SubmitQuizRequest {
  answers: QuizAnswer[]
}

export interface QuizResultDetail {
  question_id: string
  index: number
  type: QuestionType
  content: string
  user_answer: string
  correct_answer: string
  is_correct: boolean
  score: number
  explanation: string
  source_document: string
  source_page: number
}

export interface WeakPoint {
  knowledge_point: string
  document: string
  error_count: number
}

export interface QuizResult {
  quiz_id: string
  total_score: number
  correct_count: number
  total_count: number
  accuracy: number
  details: QuizResultDetail[]
  weak_points: WeakPoint[]
  submitted_at: string
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  question_count: number
  status: QuizStatus
  score?: number
  accuracy?: number
  created_at: string
  submitted_at?: string
}

export interface WrongQuestion {
  question_id: string
  quiz_id: string
  type: QuestionType
  content: string
  user_answer: string
  correct_answer: string
  explanation: string
  source_document: string
  created_at: string
}

// 测评删除响应
export interface QuizDeleteResult {
  deleted: string
  title: string
  status: QuizStatus
}

export interface QuizClearResult {
  deleted_count: number
}

// ---- 进度 (Progress) ----

export interface ProgressOverview {
  total_documents: number
  total_quizzes: number
  total_quiz_questions: number
  avg_accuracy: number
  study_days_this_week: number
  total_chunks: number
  last_activity: string
}

export interface KnowledgePoint {
  knowledge_point: string
  document_name: string
  mastery_level: number
  total_questions: number
  correct_count: number
  last_tested: string
}

// ---- 周报 (Report) ----

export interface WeekWeakPoint {
  point: string
  accuracy: number
  suggestion: string
}

export interface ReportContent {
  summary: string
  study_time_hours: number
  new_documents: number
  quiz_count: number
  avg_score: number
  accuracy_trend: string
  weak_points: WeekWeakPoint[]
  weekly_suggestion: string
}

export interface WeeklyReport {
  id: string
  week_start: string
  week_end: string
  content: ReportContent
  generated_at: string
}

export interface GenerateReportRequest {
  week_start?: string
  week_end?: string
}

export interface ReportListItem {
  id: string
  week_start: string
  week_end: string
  avg_score: number
  quiz_count: number
  generated_at: string
}

// ---- 设置 (Settings) ----

export interface Settings {
  llm_provider: string
  llm_model: string
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  top_k_default: number
}

export interface UpdateSettingsRequest {
  openai_api_key?: string
  openai_base_url?: string
  llm_model?: string
  chunk_size?: number
}

// ---- 向量数据库 (VectorDB) ----

export interface ChunkItem {
  id: string
  document_id: string
  document_name: string
  chunk_index: number
  content: string
  chroma_id: string
  page_number: number | null
  section_title: string | null
  token_count: number | null
  created_at: string
}

export interface ChunkListData {
  total: number
  page: number
  page_size: number
  items: ChunkItem[]
}

export interface DocChunkStat {
  document_id: string
  document_name: string
  chunk_count: number
}

export interface VectorDBStats {
  collection_name: string
  distance_metric: string
  chroma_count: number
  sqlite_count: number
  synced: boolean
  avg_tokens_per_chunk: number
  embedding_model: string
  by_document: DocChunkStat[]
}
