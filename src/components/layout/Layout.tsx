import { Outlet } from 'react-router-dom'
import { Navbar } from '@/components/layout/Navbar'
import { ToastContainer } from '@/components/common/Toast'

export function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="pt-14">
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  )
}
