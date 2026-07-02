import { useLocation } from 'react-router-dom'
import { Bell } from 'lucide-react'

const TITLES: Record<string, string> = {
  '/': 'Portfolio Dashboard',
  '/msmes': 'MSME Directory',
  '/analytics': 'Need Analytics',
  '/recommendations': 'Product Recommendations',
  '/funnel': 'Conversion Funnel',
}

export function Topbar() {
  const location = useLocation()
  const title = TITLES[location.pathname] ?? 'MSME Pulse'

  const now = new Date().toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })

  return (
    <header className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
      </div>
      <div className="topbar-right">
        <span className="topbar-badge">{now} IST</span>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: 'var(--text-secondary)',
          transition: 'all 0.2s'
        }}>
          <Bell size={16} />
        </div>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'var(--gradient-brand)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', fontWeight: 700, color: 'white',
          flexShrink: 0,
        }}>RM</div>
      </div>
    </header>
  )
}
