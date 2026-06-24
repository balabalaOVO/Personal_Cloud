import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './api/client'
import LoginPage from './pages/LoginPage'
import FilePage from './pages/FilePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <FilePage />
          </RequireAuth>
        }
      />
      <Route
        path="/files/*"
        element={
          <RequireAuth>
            <FilePage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
