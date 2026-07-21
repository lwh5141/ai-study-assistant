import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { Layout } from '@/components/layout/Layout'

const StudyPage = lazy(() => import('@/pages/StudyPage').then(m => ({ default: m.StudyPage })))
const DocumentsPage = lazy(() => import('@/pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })))
const QuizPage = lazy(() => import('@/pages/QuizPage').then(m => ({ default: m.QuizPage })))
const ProgressPage = lazy(() => import('@/pages/ProgressPage').then(m => ({ default: m.ProgressPage })))
const ReportPage = lazy(() => import('@/pages/ReportPage').then(m => ({ default: m.ReportPage })))
const VectorDBPage = lazy(() => import('@/pages/VectorDBPage').then(m => ({ default: m.VectorDBPage })))

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin" />
    </div>
  )
}

function NotFoundPage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <p className="text-6xl font-light text-gray-300 mb-4">404</p>
        <p className="text-gray-500">页面不存在</p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<StudyPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="quiz" element={<QuizPage />} />
            <Route path="progress" element={<ProgressPage />} />
            <Route path="report" element={<ReportPage />} />
            <Route path="vectordb" element={<VectorDBPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
