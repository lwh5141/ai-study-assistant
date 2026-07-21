import { useState, lazy, Suspense } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronRight, User, Sparkles } from 'lucide-react'
import type { ChatSource } from '@/types/api'

const SyntaxHighlighter = lazy(() =>
  import('react-syntax-highlighter/dist/esm/prism').then(m => ({ default: m.default }))
)
const oneLightPromise = import('react-syntax-highlighter/dist/esm/styles/prism').then(m => m.oneLight)

// 缓存 style 对象
let cachedStyle: typeof import('react-syntax-highlighter/dist/esm/styles/prism').oneLight | null = null
function getOneLightStyle() {
  if (!cachedStyle) {
    // 同步返回 null，组件会在 style 加载后通过 Suspense 重新渲染
    oneLightPromise.then(s => { cachedStyle = s })
  }
  return cachedStyle
}

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
}

/** Markdown 渲染组件，手动定义各元素样式（不依赖 @tailwindcss/typography） */
function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-lg font-semibold text-gray-900 mt-4 mb-2 first:mt-0">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-semibold text-gray-900 mt-3 mb-1.5 first:mt-0">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold text-gray-900 mt-3 mb-1 first:mt-0">
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-sm font-medium text-gray-800 mt-2 mb-1 first:mt-0">
            {children}
          </h4>
        ),
        p: ({ children }) => (
          <p className="text-sm text-gray-700 leading-relaxed my-1.5 first:mt-0 last:mb-0">
            {children}
          </p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc pl-5 text-sm text-gray-700 my-1.5 space-y-0.5">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal pl-5 text-sm text-gray-700 my-1.5 space-y-0.5">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-sm text-gray-700 leading-relaxed">{children}</li>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-primary-300 bg-primary-50/50 pl-3 py-1 my-2 text-sm text-gray-600 rounded-r">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="my-3 border-gray-200" />,
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full text-sm border border-gray-200 rounded">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-gray-50">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-1.5 text-left font-medium text-gray-700 border-b border-gray-200">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-1.5 text-gray-600 border-b border-gray-100">
            {children}
          </td>
        ),
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '')
          const codeText = String(children).replace(/\n$/, '')
          const isInline = !match && !codeText.includes('\n')

          if (isInline) {
            return (
              <code
                className="bg-gray-100 text-primary-700 rounded px-1 py-0.5 text-[0.8125rem]"
                {...props}
              >
                {codeText}
              </code>
            )
          }

          const style = getOneLightStyle()
          return (
            <Suspense fallback={<pre className="bg-gray-100 rounded-lg p-4 text-sm overflow-x-auto">{codeText}</pre>}>
              {style ? (
                <SyntaxHighlighter
                  style={style}
                  language={match ? match[1] : 'text'}
                  PreTag="div"
                  customStyle={{
                    borderRadius: '0.5rem',
                    fontSize: '0.8125rem',
                    margin: '0.75rem 0',
                    padding: '1rem',
                  }}
                >
                  {codeText}
                </SyntaxHighlighter>
              ) : (
                <pre className="bg-gray-100 rounded-lg p-4 text-sm overflow-x-auto">{codeText}</pre>
              )}
            </Suspense>
          )
        },
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:underline"
          >
            {children}
          </a>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-gray-900">{children}</strong>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

export function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false)
  const isUser = role === 'user'
  const hasSources = sources && sources.length > 0
  const isEmpty = !content || content.trim() === ''

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* 头像 */}
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-gray-100 text-gray-500'
            : 'bg-primary-50 text-primary-500'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </div>

      {/* 消息气泡 */}
      <div
        className={`max-w-[75%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-white text-gray-900 border border-gray-200'
            : 'bg-gray-50 text-gray-900 border border-gray-100'
        }`}
      >
        {/* 消息内容 */}
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{content}</p>
        ) : isEmpty ? (
          /* 流式输出中，显示打字动画 */
          <div className="flex items-center gap-1.5 py-1">
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        ) : (
          <MarkdownContent content={content} />
        )}

        {/* 资料来源引用（仅 AI 消息，且有引用时显示） */}
        {!isUser && hasSources && !isEmpty && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <button
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              {sourcesExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
              引用来源（{sources!.length}）
            </button>

            {sourcesExpanded && (
              <div className="mt-2 space-y-2">
                {sources!.map((source, idx) => (
                  <div
                    key={idx}
                    className="bg-white rounded border border-gray-200 p-2.5 text-xs"
                  >
                    <div className="flex items-center gap-2 mb-1 text-gray-500">
                      <span className="font-medium text-gray-700">
                        {source.document_name}
                      </span>
                      <span>第 {source.page} 页</span>
                      <span className="text-gray-300">
                        相关度 {(source.relevance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-gray-600 leading-relaxed line-clamp-4">
                      {source.excerpt}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
