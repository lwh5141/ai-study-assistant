import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, Loader2 } from 'lucide-react'

const ACCEPTED_TYPES: Record<string, string[]> = {
  'application/pdf': ['.pdf'],
  'application/vnd.ms-powerpoint': ['.ppt'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
}

const ACCEPTED_EXTENSIONS = Object.values(ACCEPTED_TYPES).flat().join(',')
const ACCEPTED_MIME_TYPES = Object.keys(ACCEPTED_TYPES).join(',')

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function validateFile(file: File): string | null {
  // 检查扩展名
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  const allExtensions = Object.values(ACCEPTED_TYPES).flat()
  if (!allExtensions.includes(ext)) {
    return `不支持的文件格式（${ext}），仅支持 PDF、PPT、Word、Markdown、TXT`
  }
  if (file.size > MAX_FILE_SIZE) {
    return `文件过大（${formatFileSize(file.size)}），上限 50MB`
  }
  if (file.size === 0) {
    return '文件为空'
  }
  return null
}

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>
  uploading: boolean
}

export function UploadZone({ onUpload, uploading }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File) => {
      const err = validateFile(file)
      if (err) {
        setError(err)
        setSelectedFile(null)
        return
      }
      setError(null)
      setSelectedFile(file)
    },
    [],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleClick = () => {
    inputRef.current?.click()
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    // 重置 input 以允许重复选择同一文件
    e.target.value = ''
  }

  const handleUploadClick = async () => {
    if (!selectedFile || uploading) return
    setError(null)
    try {
      await onUpload(selectedFile)
      setSelectedFile(null)
    } catch {
      // 错误由父组件通过 toast 处理
    }
  }

  return (
    <div className="space-y-3">
      {/* 拖拽区域 */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all cursor-pointer ${
          isDragOver
            ? 'border-amber-400 bg-amber-50'
            : 'border-gray-300 bg-white hover:border-gray-400'
        } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleInputChange}
          className="hidden"
        />

        {uploading ? (
          <>
            <Loader2 className="w-10 h-10 text-primary-400 animate-spin mb-3" />
            <p className="text-sm text-gray-500">正在上传...</p>
          </>
        ) : (
          <>
            <div
              className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors ${
                isDragOver ? 'bg-amber-100 text-amber-600' : 'bg-gray-100 text-gray-400'
              }`}
            >
              <Upload className="w-6 h-6" />
            </div>
            <p className="text-sm text-gray-600 mb-1">
              拖拽文件到此处，或<span className="text-primary-600">点击选择</span>
            </p>
            <p className="text-xs text-gray-400">
              支持 PDF、PPT、Word、Markdown、TXT，单文件上限 50MB
            </p>
          </>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 已选文件 + 上传按钮 */}
      {selectedFile && !uploading && !error && (
        <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="w-5 h-5 text-gray-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            onClick={handleUploadClick}
            className="shrink-0 rounded-lg bg-primary-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            上传
          </button>
        </div>
      )}
    </div>
  )
}
