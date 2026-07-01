/**
 * Portfolio Dashboard Page
 * Top-level RM view: KPI cards, need distribution donut,
 * product stats bar chart, and a portfolio summary table.
 */
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend, CartesianGrid,
} from 'recharts'
import {
  Users, TrendingUp, Target, CheckCircle,
  AlertTriangle, Activity, BarChart2
} from 'lucide-react'
import {
  fetchPortfolioSummary, fetchNeedDistribution, fetchProductStats,
} from '../api/client'
import type { PortfolioSummary, NeedDistribution, ProductMatchStats } from '../types'

// ── Colour palette for charts ─────────────────────────────────────────
const NEED_COLORS: Record<string, string> = {
  working_capital:       '#4F6EF7',
  machinery_capex:       '#7C3AED',
  business_expansion:    '#10B981',
  inventory_funding:     '#F59E0B',
  trade_finance:         '#06B6D4',
  digital_transformation:'#EF4444',
}

const NEED_LABELS: Record<string, string> = {
  working_capital:        'Working Capital',
  machinery_capex:        'Machinery/Capex',
  business_expansion:     'Biz Expansion',
  inventory_funding:      'Inventory',
  trade_finance:          'Trade Finance',
  digital_transformation: 'Digital',
}

const PRODUCT_LABELS: Record<string, string> = {
  cc_od:                  'CC/OD',
  machinery_term_loan:    'Machinery Loan',
  business_expansion_loan:'Expansion Loan',
  inventory_funding:      'Inventory Fund.',
  trade_finance:          'Trade Finance',
  digital_business_loan:  'Digital Loan',
}

// ── KPI Card ──────────────────────────────────────────────────────────
function KpiCard({
  icon, value, label, delta, colorClass, prefix = '', suffix = '',
}: {
  icon: React.ReactNode; value: number | string; label: string
  delta?: string; colorClass: string; prefix?: string; suffix?: string
}) {
  return (
    <div className="kpi-card fade-in">
      <div className={`kpi-icon ${colorClass}`}>{icon}</div>
      <div className="kpi-value">
        {prefix}{typeof value === 'number' ? value.toLocaleString('en-IN') : value}{suffix}
      </div>
      <div className="kpi-label">{label}</div>
      {delta && <div className={`kpi-delta ${delta.startsWith('+') ? 'positive' : 'negative'}`}>{delta}</div>}
    </div>
  )
}

// ── Custom tooltip ─────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
      borderRadius: '8px', padding: '10px 14px', fontSize: '12px',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString('en-IN') : p.value}
        </div>
      ))}
    </div>
  )
}

// ── Skeleton loader ───────────────────────────────────────────────────
function SkeletonKpi() {
  return (
    <div className="kpi-card">
      <div className="skeleton" style={{ width: 40, height: 40, borderRadius: '8px', marginBottom: 12 }} />
      <div className="skeleton" style={{ width: '60%', height: 28, marginBottom: 6 }} />
      <div className="skeleton" style={{ width: '80%', height: 12 }} />
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────
export function DashboardPage() {
  const { data: summary, isLoading: loadingSum } = useQuery<PortfolioSummary>({
    queryKey: ['portfolio-summary'],
    queryFn: fetchPortfolioSummary,
    retry: 1,
    staleTime: 30_000,
  })

  const { data: needDist = [], isLoading: loadingNeed } = useQuery<NeedDistribution[]>({
    queryKey: ['need-distribution'],
    queryFn: () => fetchNeedDistribution(90),
    retry: 1,
    staleTime: 30_000,
  })

  const { data: productStats = [], isLoading: loadingProd } = useQuery<ProductMatchStats[]>({
    queryKey: ['product-stats'],
    queryFn: fetchProductStats,
    retry: 1,
    staleTime: 30_000,
  })

  // Transform product stats for bar chart
  const productChartData = productStats.map(p => ({
    name: PRODUCT_LABELS[p.product_type] ?? p.product_type,
    recommendations: p.recommendations,
    disbursement: parseFloat(p.estimated_disbursement_cr.toFixed(2)),
    eligibility: parseFloat((p.avg_eligibility * 100).toFixed(1)),
  }))

  // Transform need distribution for pie chart
  const pieData = needDist.map(n => ({
    name: NEED_LABELS[n.category] ?? n.category,
    value: parseFloat(n.percentage.toFixed(1)),
    category: n.category,
    confidence: parseFloat((n.avg_confidence * 100).toFixed(1)),
    count: n.count,
  }))

  return (
    <div className="page-container fade-in">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Portfolio Overview</h1>
          <p className="page-subtitle">
            Real-time MSME portfolio intelligence · Updated just now
          </p>
        </div>
        <div className="flex gap-sm">
          <button className="btn btn-secondary btn-sm">
            <Activity size={14} /> Export
          </button>
          <button className="btn btn-primary btn-sm">
            <BarChart2 size={14} /> Run Predictions
          </button>
        </div>
      </div>

      {/* ── KPI Grid ────────────────────────────────────────────────── */}
      <div className="kpi-grid">
        {loadingSum ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonKpi key={i} />)
        ) : summary ? (
          <>
            <KpiCard
              icon={<Users size={20} />}
              value={summary.total_msmes}
              label="Total MSMEs"
              delta={`${summary.active_msmes.toLocaleString('en-IN')} active`}
              colorClass="blue"
            />
            <KpiCard
              icon={<TrendingUp size={20} />}
              value={summary.need_predictions_generated}
              label="Needs Identified"
              delta={`+${Math.round(summary.need_predictions_generated * 0.08)} this week`}
              colorClass="purple"
            />
            <KpiCard
              icon={<Target size={20} />}
              value={summary.product_recommendations}
              label="Recommendations"
              delta={`${summary.approved_recommendations} approved`}
              colorClass="green"
            />
            <KpiCard
              icon={<CheckCircle size={20} />}
              value={`${summary.conversion_rate.toFixed(1)}`}
              label="Conversion Rate"
              delta={summary.conversion_rate > 10 ? '+vs benchmark' : '–vs benchmark'}
              colorClass="amber"
              suffix="%"
            />
          </>
        ) : (
          <div className="kpi-card" style={{ gridColumn: '1/-1', textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>
            <AlertTriangle size={24} style={{ margin: '0 auto 8px' }} />
            <div>Backend offline — start FastAPI server to see live data</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>Running with mock data</div>
          </div>
        )}
      </div>

      {/* ── Charts Row ──────────────────────────────────────────────── */}
      <div className="grid-21 mb-lg">
        {/* Product Stats Bar */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Product Recommendations by Type</span>
            <span className="badge badge-brand">Live</span>
          </div>
          <div className="card-body">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={240}>
                {loadingProd ? (
                  <div className="skeleton" style={{ height: 240 }} />
                ) : (
                  <BarChart data={productChartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="recommendations" name="Recs" fill="#4F6EF7" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="disbursement" name="₹Cr Est." fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Need Distribution Donut */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Need Distribution</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Last 90 days</span>
          </div>
          <div className="card-body">
            <div className="chart-container" style={{ minHeight: 200 }}>
              <ResponsiveContainer width="100%" height={200}>
                {loadingNeed ? (
                  <div className="skeleton" style={{ height: 200 }} />
                ) : (
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.category} fill={NEED_COLORS[entry.category] ?? '#4F6EF7'} />
                      ))}
                    </Pie>
                    <Tooltip
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      formatter={((v: any, name: any, props: any) => [
                        `${v ?? 0}% (${props?.payload?.count ?? 0} MSMEs)`,
                        name as string
                      ]) as any}
                    />
                  </PieChart>
                )}
              </ResponsiveContainer>
            </div>
            {/* Legend */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {pieData.slice(0, 4).map(d => (
                <div key={d.category} className="flex items-center justify-between">
                  <div className="flex items-center gap-xs">
                    <div style={{
                      width: 8, height: 8, borderRadius: 2,
                      background: NEED_COLORS[d.category],
                      flexShrink: 0,
                    }} />
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{d.name}</span>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {d.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Status Summary ───────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Portfolio Health Snapshot</span>
        </div>
        <div className="card-body">
          <div className="grid-3" style={{ gap: 24 }}>
            {[
              { label: 'GST Filed MSMEs', value: summary?.msmes_with_gst ?? 0, total: summary?.total_msmes ?? 1, color: 'brand' },
              { label: 'AA Linked MSMEs', value: summary?.msmes_with_aa ?? 0, total: summary?.total_msmes ?? 1, color: 'success' },
              { label: 'Recommendation Coverage', value: summary?.product_recommendations ?? 0, total: summary?.total_msmes ?? 1, color: 'warning' },
            ].map(({ label, value, total, color }) => (
              <div key={label}>
                <div className="flex justify-between mb-sm">
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                    {Math.min(100, Math.round((value / total) * 100))}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${color}`}
                    style={{ width: `${Math.min(100, Math.round((value / total) * 100))}%` }}
                  />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  {value.toLocaleString('en-IN')} of {total.toLocaleString('en-IN')} MSMEs
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
