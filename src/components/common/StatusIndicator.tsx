import { useConnectionStatus, type ConnectionState } from '@/hooks/useConnectionStatus'
import { Wifi, WifiOff, Clock, Loader2 } from 'lucide-react'

const STATUS_CONFIG: Record<ConnectionState, {
  icon: typeof Wifi
  label: string
  dotClass: string
  textClass: string
  iconClass: string
  pulse: boolean
}> = {
  online: {
    icon: Wifi,
    label: '在线',
    dotClass: 'bg-green-500',
    textClass: 'text-green-600',
    iconClass: 'text-green-500',
    pulse: true,
  },
  delayed: {
    icon: Clock,
    label: '延迟',
    dotClass: 'bg-yellow-500',
    textClass: 'text-yellow-600',
    iconClass: 'text-yellow-500',
    pulse: false,
  },
  offline: {
    icon: WifiOff,
    label: '离线',
    dotClass: 'bg-red-500',
    textClass: 'text-red-600',
    iconClass: 'text-red-500',
    pulse: false,
  },
  checking: {
    icon: Loader2,
    label: '检测中',
    dotClass: 'bg-gray-300',
    textClass: 'text-gray-400',
    iconClass: 'text-gray-400',
    pulse: false,
  },
}

export function StatusIndicator() {
  const status = useConnectionStatus()
  const config = STATUS_CONFIG[status]
  const Icon = config.icon

  return (
    <div className="flex items-center gap-1.5 select-none">
      {/* 状态灯 + 图标 */}
      <span className="relative flex items-center justify-center w-5 h-5">
        <span
          className={`absolute inset-0 rounded-full opacity-30 ${
            config.pulse ? 'animate-ping' : ''
          } ${config.dotClass}`}
        />
        <Icon
          className={`relative w-3.5 h-3.5 ${config.iconClass} ${
            status === 'checking' ? 'animate-spin' : ''
          }`}
        />
      </span>
      {/* 状态文字 */}
      <span className={`text-xs font-medium ${config.textClass}`}>
        {config.label}
      </span>
    </div>
  )
}
