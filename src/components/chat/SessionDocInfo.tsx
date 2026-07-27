import { FileText } from 'lucide-react'
import type { Document } from '@/types/api'

interface SessionDocInfoProps {
  documents: Document[]
  selectedIds: string[]
}

/**
 * 会话引用资料信息展示框
 *
 * 位于"选择资料"按钮与"新对话"按钮之间，显示当前对话所引用的资料。
 * - 无引用资料：虚线边框 + "无引用资料"占位
 * - 有引用资料：显示文件名（1份）或 "N 份资料"（多份），hover 展示完整列表
 */
export function SessionDocInfo({ documents, selectedIds }: SessionDocInfoProps) {
  const matchedDocs = documents.filter((d) => selectedIds.includes(d.id))
  const noneSelected = selectedIds.length === 0 || matchedDocs.length === 0

  if (noneSelected) {
    return (
      <div className="shrink hidden sm:flex items-center gap-1.5 rounded-lg border border-dashed border-gray-200 bg-gray-50/50 px-3 py-2 text-xs text-gray-400">
        <FileText className="w-3.5 h-3.5" />
        <span className="truncate">无引用资料</span>
      </div>
    )
  }

  // hover tooltip 展示完整文件名列表
  const tooltipText = matchedDocs.map((d) => d.filename).join('\n')

  return (
    <div
      className="shrink flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600 hover:border-primary-200 hover:bg-primary-50/30 transition-colors cursor-default"
      title={tooltipText}
    >
      <FileText className="w-3.5 h-3.5 text-primary-500 shrink-0" />
      <span className="truncate max-w-[140px]">
        {matchedDocs.length === 1
          ? matchedDocs[0].filename
          : `${matchedDocs.length} 份资料`}
      </span>
      {/* 类型标签 */}
      <span className="shrink-0 text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
        {matchedDocs[0].file_type.toUpperCase()}
      </span>
    </div>
  )
}
