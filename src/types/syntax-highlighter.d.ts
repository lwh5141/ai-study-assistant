declare module 'react-syntax-highlighter' {
  import type { ComponentType } from 'react'
  const SyntaxHighlighter: ComponentType<{
    style?: Record<string, unknown>
    language?: string
    PreTag?: string | ComponentType<{ children?: React.ReactNode }>
    customStyle?: Record<string, unknown>
    children?: string
    [key: string]: unknown
  }>
  export default SyntaxHighlighter
}

declare module 'react-syntax-highlighter/dist/esm/prism' {
  import type { ComponentType } from 'react'
  const SyntaxHighlighter: ComponentType<{
    style?: Record<string, unknown>
    language?: string
    PreTag?: string | ComponentType<{ children?: React.ReactNode }>
    customStyle?: Record<string, unknown>
    children?: string
    [key: string]: unknown
  }>
  export default SyntaxHighlighter
}

declare module 'react-syntax-highlighter/dist/esm/styles/prism' {
  export const oneLight: Record<string, unknown>
}
