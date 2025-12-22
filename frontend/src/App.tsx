import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { HomePage } from './pages/HomePage'
import { CredentialsPage } from './pages/CredentialsPage'
import { AnalysisPage } from './pages/AnalysisPage'
import { ResultsPage } from './pages/ResultsPage'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/credentials" element={<CredentialsPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/results/:id" element={<ResultsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
