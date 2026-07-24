import { useState, useRef, useEffect, cloneElement, isValidElement } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface SmartTooltipProps {
  /** tooltip 内容 */
  content: ReactNode
  /** 触发器元素（必须是单个 React 元素） */
  children: React.ReactElement
  /** 显示延迟 ms，默认 300（避免快速划过闪烁） */
  delay?: number
  /** 最大宽度 px，默认 280 */
  maxWidth?: number
  /** 额外类名 */
  className?: string
}

/**
 * 鼠标跟随型 Tooltip —— 在鼠标右上角弹出，跟随鼠标移动。
 *
 * 特性：
 * - 通过 Portal 渲染到 document.body，避免父级 overflow 裁剪
 * - 边界检测：右侧不够自动放左侧，上方不够自动放下方
 * - 延迟显示（默认 300ms），避免快速划过闪烁；鼠标移出立即隐藏
 * - 超长内容自动换行（max-w + break-words）
 * - pointer-events-none，避免遮挡 hover 检测
 *
 * @example
 * <SmartTooltip content="完整内容文本">
 *   <div>触发器</div>
 * </SmartTooltip>
 */
export function SmartTooltip({
  content,
  children,
  delay = 300,
  maxWidth = 280,
  className,
}: SmartTooltipProps) {
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const show = (clientX: number, clientY: number) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setPosition({ x: clientX, y: clientY })
      setVisible(true)
    }, delay)
  }

  const hide = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    setVisible(false)
  }

  const updatePosition = (clientX: number, clientY: number) => {
    if (!visible) return

    const tooltip = tooltipRef.current
    const tooltipW = tooltip?.offsetWidth ?? maxWidth
    const tooltipH = tooltip?.offsetHeight ?? 60
    const margin = 16

    // 默认放鼠标右上角
    let x = clientX + margin
    let y = clientY - margin

    // 右侧溢出 → 放左上角
    if (x + tooltipW > window.innerWidth) {
      x = clientX - tooltipW - margin
    }
    // 上方溢出 → 放下方
    if (y - tooltipH < 0) {
      y = clientY + margin
    }
    // 左侧溢出兜底
    if (x < 0) {
      x = margin
    }

    setPosition({ x, y })
  }

  // 注入事件到 children
  const childProps = children.props as Record<string, unknown>
  const enhancedChildren = isValidElement(children)
    ? cloneElement(children as React.ReactElement<Record<string, unknown>>, {
        onMouseEnter: (e: React.MouseEvent) => {
          show(e.clientX, e.clientY)
          ;(childProps.onMouseEnter as ((e: React.MouseEvent) => void) | undefined)?.(e)
        },
        onMouseMove: (e: React.MouseEvent) => {
          updatePosition(e.clientX, e.clientY)
          ;(childProps.onMouseMove as ((e: React.MouseEvent) => void) | undefined)?.(e)
        },
        onMouseLeave: (e: React.MouseEvent) => {
          hide()
          ;(childProps.onMouseLeave as ((e: React.MouseEvent) => void) | undefined)?.(e)
        },
      })
    : children

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  // 组件卸载或 visible 变 false 时，下次显示前重新计算
  useEffect(() => {
    if (visible && tooltipRef.current) {
      // 首次显示时位置已设置，但 tooltip 实际高度刚测得，再校准一次
      requestAnimationFrame(() => {
        if (tooltipRef.current && visible) {
          updatePosition(position.x, position.y)
        }
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible])

  return (
    <>
      {enhancedChildren}
      {visible &&
        createPortal(
          <div
            ref={tooltipRef}
            role="tooltip"
            className={cn(
              'fixed z-[100] pointer-events-none px-3 py-2 bg-gray-900 text-white text-xs rounded-md shadow-lg',
              'max-w-[280px] break-words leading-relaxed',
              'animate-in fade-in zoom-in-95 duration-150',
              className
            )}
            style={{
              left: position.x,
              top: position.y,
              maxWidth,
            }}
          >
            {content}
          </div>,
          document.body
        )}
    </>
  )
}
