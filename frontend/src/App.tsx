
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { DashboardPage } from './pages/DashboardPage'
import { MSMESearchPage } from './pages/MSMESearchPage'
import { MSMEProfilePage } from './pages/MSMEProfilePage'
import { NeedAnalyticsPage } from './pages/NeedAnalyticsPage'
import { ConversionFunnelPage } from './pages/ConversionFunnelPage'
import { LoanEligibilityPage } from './pages/LoanEligibilityPage'
import './index.css'

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function AppShell() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Topbar />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/msmes" element={<MSMESearchPage />} />
          <Route path="/msme/:id" element={<MSMEProfilePage />} />
          <Route path="/analytics" element={<NeedAnalyticsPage />} />
          <Route path="/recommendations" element={<NeedAnalyticsPage />} />
          <Route path="/funnel" element={<ConversionFunnelPage />} />
          <Route path="/loan-eligibility" element={<LoanEligibilityPage />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
