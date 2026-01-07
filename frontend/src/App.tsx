import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ErrorBoundary } from './components/common'
import { Layout } from './components/layout/Layout'
import { ThemeProvider } from './contexts/ThemeContext'
import { HomePage } from './pages/HomePage'
import { CredentialsPage } from './pages/CredentialsPage'
import { AnalysisPage } from './pages/AnalysisPage'
import { ResultsPage } from './pages/ResultsPage'
import { BrandingSettingsPage } from './pages/BrandingSettingsPage'

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/credentials" element={<CredentialsPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/results/:id" element={<ResultsPage />} />
              <Route path="/branding" element={<BrandingSettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
