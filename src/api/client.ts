// ============================================================
// API 客户端 — 统一封装所有后端请求
// 基础路径：/api/v1
// ============================================================

import type {
  ApiResponse,
  ApiError,
  PaginatedData,
  Document,
  UploadResponse,
  ChatSession,
  ChatSessionDetail,
  SendMessageRequest,
  SendMessageResponse,
  Quiz,
  GenerateQuizRequest,
  SubmitQuizRequest,
  QuizResult,
  QuizHistoryItem,
  QuizDeleteResult,
  QuizClearResult,
  WrongQuestion,
  ProgressOverview,
  KnowledgePoint,
  WeeklyReport,
  GenerateReportRequest,
  ReportListItem,
  Settings,
  UpdateSettingsRequest,
  ChunkListData,
  ChunkItem,
  VectorDBStats,
} from '@/types/api'

const BASE_URL = '/api/v1'

// ---- 错误类 ----

export class ApiRequestError extends Error {
  code: number
  status: number

  constructor(message: string, code: number, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
  }
}

// ---- 通用请求封装 ----

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  }

  // 非 FormData 请求自动加 Content-Type
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(url, { ...options, headers })

  if (!response.ok) {
    let errorData: Partial<ApiError> = {}
    try {
      errorData = await response.json()
    } catch {
      // 响应体不是 JSON
    }
    throw new ApiRequestError(
      errorData.message || `请求失败 (${response.status})`,
      errorData.code || 9999,
      response.status,
    )
  }

  const result: ApiResponse<T> = await response.json()
  return result.data
}

// ---- 公共请求方法 ----

function get<T>(endpoint: string, params?: Record<string, string | number | undefined>): Promise<T> {
  let url = endpoint
  if (params) {
    const search = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) search.set(k, String(v))
    }
    const qs = search.toString()
    if (qs) url += `?${qs}`
  }
  return request<T>(url, { method: 'GET' })
}

function post<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

function put<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

function del<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'DELETE' })
}

// ---- 资料管理 ----

export async function uploadDocument(
  file: File,
  overwrite = false,
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('overwrite', String(overwrite))
  return request<UploadResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
  })
}

export function getDocuments(params?: {
  page?: number
  page_size?: number
  status?: string
}): Promise<PaginatedData<Document>> {
  return get<PaginatedData<Document>>('/documents', params as Record<string, string | number | undefined>)
}

export function getDocument(id: string): Promise<Document> {
  return get<Document>(`/documents/${id}`)
}

export function deleteDocument(id: string): Promise<{ message: string }> {
  return del<{ message: string }>(`/documents/${id}`)
}

export function reparseDocument(id: string): Promise<Document> {
  return post<Document>(`/documents/${id}/reparse`)
}

// ---- 对话问答 ----

export function sendMessage(
  data: SendMessageRequest,
): Promise<SendMessageResponse> {
  return post<SendMessageResponse>('/chat', data)
}

/** SSE 流式对话（后续实现） */
export function sendMessageStream(
  data: SendMessageRequest,
  onToken: (token: string) => void,
  onDone: (result: SendMessageResponse) => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()

  fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`SSE error: ${response.status}`)
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6)
            if (payload === '[DONE]') continue
            try {
              const parsed = JSON.parse(payload)
              if (parsed.token) {
                onToken(parsed.token)
              } else if (parsed.sources) {
                onDone(parsed as SendMessageResponse)
              }
            } catch {
              onToken(payload)
            }
          }
        }
      }
    })
    .catch(onError)

  return controller
}

export function getSessions(): Promise<ChatSession[]> {
  return get<ChatSession[]>('/chat/sessions')
}

export function getSession(id: string): Promise<ChatSessionDetail> {
  return get<ChatSessionDetail>(`/chat/sessions/${id}`)
}

export function deleteSession(id: string): Promise<{ message: string }> {
  return del<{ message: string }>(`/chat/sessions/${id}`)
}

export function renameSession(id: string, title: string): Promise<ChatSession> {
  return put<ChatSession>(`/chat/sessions/${id}`, { title })
}

// ---- 测评 ----

export function generateQuiz(data?: GenerateQuizRequest): Promise<Quiz> {
  return post<Quiz>('/quiz/generate', data || {})
}

export function submitQuiz(
  quizId: string,
  data: SubmitQuizRequest,
): Promise<QuizResult> {
  return post<QuizResult>(`/quiz/${quizId}/submit`, data)
}

export function getQuizResult(quizId: string): Promise<QuizResult> {
  return get<QuizResult>(`/quiz/${quizId}/result`)
}

export function getQuizHistory(params?: {
  page?: number
  page_size?: number
  status?: string
}): Promise<PaginatedData<QuizHistoryItem>> {
  return get<PaginatedData<QuizHistoryItem>>('/quiz/history', params as Record<string, string | number | undefined>)
}

export function getWrongQuestions(params?: {
  document_id?: string
  page?: number
}): Promise<PaginatedData<WrongQuestion>> {
  return get<PaginatedData<WrongQuestion>>('/quiz/wrong-questions', params as Record<string, string | number | undefined>)
}

// ---- 测评删除 ----

export function deleteQuiz(quizId: string): Promise<QuizDeleteResult> {
  return del<QuizDeleteResult>(`/quiz/${quizId}`)
}

export function clearQuizHistory(params?: {
  /** 仅清理指定状态：'ready' / 'submitted'。不传则清空全部 */
  status?: string
}): Promise<QuizClearResult> {
  let url = '/quiz'
  if (params?.status) {
    url += `?status=${encodeURIComponent(params.status)}`
  }
  return request<QuizClearResult>(url, { method: 'DELETE' })
}

// ---- 进度 ----

export function getProgressOverview(): Promise<ProgressOverview> {
  return get<ProgressOverview>('/progress/overview')
}

export function getKnowledgePoints(documentId?: string): Promise<KnowledgePoint[]> {
  return get<KnowledgePoint[]>(
    '/progress/knowledge',
    documentId ? { document_id: documentId } : undefined,
  )
}

// ---- 周报 ----

export function generateReport(data?: GenerateReportRequest): Promise<WeeklyReport> {
  return post<WeeklyReport>('/report/generate', data || {})
}

export function getReportList(): Promise<ReportListItem[]> {
  return get<ReportListItem[]>('/report/list')
}

export function getReport(id: string): Promise<WeeklyReport> {
  return get<WeeklyReport>(`/report/${id}`)
}

// ---- 设置 ----

export function getSettings(): Promise<Settings> {
  return get<Settings>('/settings')
}

export function updateSettings(data: UpdateSettingsRequest): Promise<Settings> {
  return put<Settings>('/settings', data)
}

// ---- 向量数据库 ----

export function getChunks(params?: {
  page?: number
  page_size?: number
  document_id?: string
  search?: string
}): Promise<ChunkListData> {
  return get<ChunkListData>('/vectordb/chunks', params as Record<string, string | number | undefined>)
}

export function getChunk(id: string): Promise<ChunkItem> {
  return get<ChunkItem>(`/vectordb/chunks/${id}`)
}

export function getVectorDBStats(): Promise<VectorDBStats> {
  return get<VectorDBStats>('/vectordb/stats')
}
