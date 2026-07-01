import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, TrendingUp, Target, Activity,
  GitBranch, ChevronRight, Zap
} from 'lucide-react'

interface NavItem {
  label: string
  icon: React.ReactNode
  to: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Portfolio', icon: <LayoutDashboard size={18} />, to: '/' },
  { label: 'MSME Search', icon: <Users size={18} />, to: '/msmes' },
  { label: 'Need Analytics', icon: <TrendingUp size={18} />, to: '/analytics' },
  { label: 'Recommendations', icon: <Target size={18} />, to: '/recommendations' },
  { label: 'Conversion Funnel', icon: <GitBranch size={18} />, to: '/funnel' },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Zap size={16} />
        </div>
        <div>
          <div className="sidebar-logo-text">MSME Pulse</div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '1px' }}>
            IDBI Innovate 2026
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Main</div>
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            {item.icon}
            <span style={{ flex: 1 }}>{item.label}</span>
            <ChevronRight size={14} style={{ opacity: 0.3 }} />
          </NavLink>
        ))}

        <div className="nav-section-label" style={{ marginTop: '16px' }}>System</div>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-item"
        >
          <Activity size={18} />
          <span style={{ flex: 1 }}>API Docs</span>
          <ChevronRight size={14} style={{ opacity: 0.3 }} />
        </a>
      </nav>

      {/* Footer badge */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        textAlign: 'center',
      }}>
        Track 3 · AI/ML Proactive Lending
      </div>
    </aside>
  )
}
