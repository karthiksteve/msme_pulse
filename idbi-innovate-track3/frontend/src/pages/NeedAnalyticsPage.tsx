/**
 * Need Analytics Page
 * Detailed breakdown of need categories with trend lines and confidence.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts'
import { fetchNeedDistribution, fetchProductStats } from '../api/client'
import type { NeedDistribution, ProductMatchStats } from '../types'

const NEED_COLORS: Record<string, string> = {
  working_capital: '#4F6EF7',
  machinery_capex: '#7C3AED',
  business_expansion: '#10B981',
  inventory_funding: '#F59E0B',
  trade_finance: '#06B6D4',
  digital_transformation: '#EF4444',
}

const NEED_LABELS: Record<string, string> = {
  working_capital: 'Working Capital',
  machinery_capex: 'Machinery/Capex',
  business_expansion: 'Business Expansion',
  inventory_funding: 'Inventory Funding',
  trade_finance: 'Trade Finance',
  digital_transformation: 'Digital Transformation',
}

const PRODUCT_LABELS: Record<string, string> = {
  cc_od: 'CC/OD',
  machinery_term_loan: 'Machinery Loan',
  business_expansion_loan: 'Expansion Loan',
  inventory_funding: 'Inventory Fund.',
  trade_finance: 'Trade Finance',
  digital_business_loan: 'Digital Loan',
}

export function NeedAnalyticsPage() {
  const [days, setDays] = useState(90)

  const { data: needDist = [], isLoading: loadingNeed } = useQuery<NeedDistribution[]>({
    queryKey: ['need-distribution', days],
    queryFn: () => fetchNeedDistribution(days),
    staleTime: 30_000,
  })

  const { data: productStats = [] } = useQuery<ProductMatchStats[]>({
    queryKey: ['product-stats'],
    queryFn: fetchProductStats,
    staleTime: 30_000,
  })

  const radarData = needDist.map(n => ({
    need: NEED_LABELS[n.category] ?? n.category,
    percentage: parseFloat(n.percentage.toFixed(1)),
    confidence: parseFloat((n.avg_confidence * 100).toFixed(1)),
    count: n.count,
  }))

  const productChartData = productStats.map(p => ({
    name: PRODUCT_LABELS[p.product_type] ?? p.product_type,
    disbursement: parseFloat(p.estimated_disbursement_cr.toFixed(2)),
    eligibility: parseFloat((p.avg_eligibility * 100).toFixed(1)),
    count: p.recommendations,
  }))

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Need Analytics</h1>
          <p className="page-subtitle">AI-detected MSME needs across portfolio</p>
        </div>
        <div className="flex gap-sm">
          {[30, 60, 90, 180].map(d => (
            <button
              key={d}
              className={`btn btn-sm ${days === d ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Need breakdown table */}
      <div className="grid-2 mb-lg">
        {/* Radar chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Need Coverage Radar</span>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={100}>
                <PolarGrid stroke="var(--border-subtle)" />
                <PolarAngleAxis dataKey="need" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar name="% MSMEs" dataKey="percentage" stroke="#4F6EF7" fill="#4F6EF7" fillOpacity={0.25} />
                <Radar name="Confidence" dataKey="confidence" stroke="#10B981" fill="#10B981" fillOpacity={0.15} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Need breakdown table */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Need Category Breakdown</span>
          </div>
          <div className="card-body">
            {loadingNeed ? (
              Array.from({ length: 6 }).map((_, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div className="skeleton" style={{ height: 14, width: '60%', marginBottom: 6 }} />
                  <div className="skeleton" style={{ height: 6 }} />
                </div>
              ))
            ) : (
              needDist
                .sort((a, b) => b.percentage - a.percentage)
                .map(n => (
                  <div key={n.category} style={{ marginBottom: 14 }}>
                    <div className="flex justify-between mb-sm">
                      <div className="flex items-center gap-xs">
                        <div style={{
                          width: 10, height: 10, borderRadius: 3,
                          background: NEED_COLORS[n.category], flexShrink: 0,
                        }} />
                        <span style={{ fontSize: 13 }}>{NEED_LABELS[n.category]}</span>
                      </div>
                      <div className="flex gap-md" style={{ fontSize: 12 }}>
                        <span style={{ color: 'var(--text-muted)' }}>{n.count.toLocaleString('en-IN')} MSMEs</span>
                        <span className="font-mono" style={{ fontWeight: 700 }}>{n.percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="progress-bar">
                      <div style={{
                        width: `${n.percentage}%`, height: '100%',
                        borderRadius: '999px',
                        background: NEED_COLORS[n.category],
                        transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
                      }} />
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                      Avg. confidence: {(n.avg_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                ))
            )}
          </div>
        </div>
      </div>

      {/* Product opportunity */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Product Opportunity Sizing</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Estimated disbursement in ₹ Crore</span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {productChartData.map(p => (
              <div key={p.name} style={{
                background: 'var(--bg-elevated)',
                borderRadius: 10, padding: '14px 16px',
                border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{p.name}</div>
                <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>
                  ₹{p.disbursement} Cr
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {p.count.toLocaleString('en-IN')} recommendations · {p.eligibility.toFixed(1)}% avg. eligibility
                </div>
                <div className="progress-bar" style={{ marginTop: 10 }}>
                  <div className="progress-fill brand" style={{ width: `${p.eligibility}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
