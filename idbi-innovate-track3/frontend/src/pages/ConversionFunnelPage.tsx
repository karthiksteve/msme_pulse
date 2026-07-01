/**
 * Conversion Funnel Page
 * Visualises recommendation lifecycle stages as a funnel + bar chart.
 */
import { useQuery } from '@tanstack/react-query'
import { FunnelChart, Funnel, LabelList, Tooltip, ResponsiveContainer } from 'recharts'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell } from 'recharts'
import { fetchConversionFunnel } from '../api/client'
import { GitBranch } from 'lucide-react'

const STAGES = [
  { key: 'generated', label: 'Generated',  color: '#4F6EF7' },
  { key: 'sent',      label: 'Sent to RM', color: '#7C3AED' },
  { key: 'viewed',    label: 'Viewed',     color: '#06B6D4' },
  { key: 'applied',   label: 'Applied',    color: '#F59E0B' },
  { key: 'approved',  label: 'Approved',   color: '#10B981' },
  { key: 'rejected',  label: 'Rejected',   color: '#EF4444' },
]

export function ConversionFunnelPage() {
  const { data } = useQuery<Record<string, number>>({
    queryKey: ['conversion-funnel'],
    queryFn: fetchConversionFunnel,
    retry: 1,
    staleTime: 30_000,
  })

  const funnelData = STAGES.filter(s => s.key !== 'rejected').map(s => ({
    name: s.label,
    value: data?.[s.key] ?? 0,
    fill: s.color,
  }))

  const barData = STAGES.map(s => ({
    stage: s.label,
    count: data?.[s.key] ?? 0,
    color: s.color,
  }))

  const total    = data?.generated ?? 1
  const approved = data?.approved ?? 0
  const convRate = ((approved / total) * 100).toFixed(1)

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Conversion Funnel</h1>
          <p className="page-subtitle">Recommendation lifecycle from generation to approval</p>
        </div>
      </div>

      {/* KPIs */}
      <div className="kpi-grid mb-lg">
        {[
          { label: 'Generated',  key: 'generated', colorClass: 'blue' },
          { label: 'Sent',       key: 'sent',      colorClass: 'purple' },
          { label: 'Approved',   key: 'approved',  colorClass: 'green' },
          { label: 'Rejected',   key: 'rejected',  colorClass: 'red' },
        ].map(({ label, key, colorClass }) => (
          <div className="kpi-card" key={key}>
            <div className={`kpi-icon ${colorClass}`}><GitBranch size={20} /></div>
            <div className="kpi-value">{(data?.[key] ?? 0).toLocaleString('en-IN')}</div>
            <div className="kpi-label">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        {/* Funnel chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Recommendation Funnel</span>
            <span style={{ fontSize: 12, color: 'var(--color-brand-accent)', fontWeight: 700 }}>
              {convRate}% conversion
            </span>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={340}>
              <FunnelChart>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                <Tooltip formatter={((v: any) => [Number(v ?? 0).toLocaleString('en-IN'), 'Count']) as any} />
                <Funnel dataKey="value" data={funnelData} isAnimationActive>
                  <LabelList position="right" fill="var(--text-primary)" stroke="none"
                    dataKey="name" style={{ fontSize: 12, fontWeight: 600 }} />
                  <LabelList position="center" fill="white" stroke="none"
                    dataKey="value" style={{ fontSize: 12, fontWeight: 700 }} />
                </Funnel>
              </FunnelChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stage bar chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Volume by Stage</span>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} margin={{ top: 5, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="stage" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            {/* Drop-off analysis */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>
                Stage Drop-off Analysis
              </div>
              {STAGES.slice(0, -1).map((stage, i) => {
                const curr  = data?.[stage.key] ?? 0
                const next  = data?.[STAGES[i + 1]?.key] ?? 0
                const drop  = curr > 0 ? ((curr - next) / curr * 100) : 0
                return (
                  <div key={stage.key} className="flex justify-between items-center" style={{ marginBottom: 8 }}>
                    <div className="flex gap-sm items-center">
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: stage.color }} />
                      <span style={{ fontSize: 12 }}>{stage.label} → {STAGES[i + 1]?.label}</span>
                    </div>
                    <span className="font-mono" style={{
                      fontSize: 12, fontWeight: 700,
                      color: drop > 50 ? 'var(--color-brand-danger)' :
                             drop > 25 ? 'var(--color-brand-warning)' : 'var(--color-brand-accent)',
                    }}>
                      -{drop.toFixed(0)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
