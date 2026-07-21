import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { BookOpen, FileText, FileCheck, BarChart3, FileBarChart, Database, Menu, X } from 'lucide-react'
import { StatusIndicator } from '@/components/common/StatusIndicator'
import { UserMenu } from '@/components/common/UserMenu'
import { Logo } from '@/components/common/Logo'

const tabs = [
  { to: '/', label: '学习', icon: BookOpen },
  { to: '/documents', label: '资料库', icon: FileText },
  { to: '/quiz', label: '测评', icon: FileCheck },
  { to: '/progress', label: '进度', icon: BarChart3 },
  { to: '/report', label: '报告', icon: FileBarChart },
]

export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()

  // 路由切换时关闭抽屉
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  // 抽屉打开时禁用 body 滚动
  useEffect(() => {
    if (drawerOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [drawerOpen])

  return (
    <nav className="fixed top-0 z-50 w-full bg-white border-b border-gray-200">
      <div className="flex items-center h-14 px-4 sm:px-6">
        {/* 左侧：Logo + 产品名（始终显示） */}
        <NavLink
          to="/"
          end
          className="flex items-center gap-2 shrink-0 group"
          aria-label="大模型学习助手 - 回到首页"
        >
          <Logo className="w-7 h-7 transition-transform group-hover:scale-105" />
          <span className="text-sm font-semibold text-gray-900 select-none hidden sm:inline">
            大模型学习助手
          </span>
        </NavLink>

        {/* 桌面端：横向 Tabs（≥ sm 显示） */}
        <div className="hidden sm:flex items-center gap-2 ml-6">
          {tabs.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `relative flex items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-primary-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 rounded-full mx-4" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>

        {/* 弹性空白区 */}
        <div className="flex-1" />

        {/* 桌面端右侧：向量库 + 状态 + 用户（≥ sm 显示） */}
        <div className="hidden sm:flex items-center gap-4 shrink-0">
          <NavLink
            to="/vectordb"
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? 'text-primary-600'
                  : 'text-gray-400 hover:text-gray-600'
              }`
            }
          >
            <Database className="w-4 h-4" />
            <span>向量库</span>
          </NavLink>

          <span className="w-px h-4 bg-gray-200" />

          <StatusIndicator />

          <span className="w-px h-4 bg-gray-200" />

          <UserMenu />
        </div>

        {/* 移动端：hamburger 按钮（< sm 显示） */}
        <button
          onClick={() => setDrawerOpen(true)}
          className="sm:hidden p-2 -mr-2 text-gray-600 hover:text-gray-900"
          aria-label="打开菜单"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* 移动端抽屉 */}
      {drawerOpen && (
        <div
          className="sm:hidden fixed inset-0 z-50"
          onClick={() => setDrawerOpen(false)}
        >
          {/* 遮罩 */}
          <div className="absolute inset-0 bg-black/40 animate-in fade-in duration-150" />
          {/* 抽屉面板 */}
          <div
            className="absolute right-0 top-0 h-full w-72 max-w-[80vw] bg-white shadow-xl animate-in slide-in-from-right duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 h-14 border-b border-gray-100">
              <span className="text-sm font-semibold text-gray-900">菜单</span>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-2 -mr-2 text-gray-500 hover:text-gray-900"
                aria-label="关闭菜单"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="py-2">
              {tabs.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </NavLink>
              ))}
              <div className="my-2 border-t border-gray-100" />
              <NavLink
                to="/vectordb"
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`
                }
              >
                <Database className="w-4 h-4" />
                <span>向量库</span>
              </NavLink>
            </div>
            <div className="absolute bottom-0 left-0 right-0 px-4 py-4 border-t border-gray-100 bg-gray-50">
              <div className="flex items-center justify-between">
                <StatusIndicator />
                <UserMenu />
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
