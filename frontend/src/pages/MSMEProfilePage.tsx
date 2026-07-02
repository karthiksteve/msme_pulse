/**
 * MSME 360° Profile Page
 * Full profile view: business info, 12-month GST sparkline,
 * AA liability gauge, need prediction panel with SHAP bars,
 * and product recommendation cards with status lifecycle.
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell,
} from 'recharts'
import {
  ArrowLeft, Building2, MapPin, Calendar, Shield,
  TrendingUp, AlertTriangle, CheckCircle, XCircle,
  CreditCard, Zap, RefreshCw, Target, FileText
} from 'lucide-react'
import { fetchMSMEById, updateRecommendationStatus, fetchLoanExplanationGet } from '../api/client'
import type {
  FullMSMEProfile, GSTReturn, AAAccount, NeedPrediction,
  ProductRecommendation, MSMEStatus, RecStatus,
} from '../types'

// ── Helpers ───────────────────────────────────────────────────────────
const fmtCr = (n: number) => `₹${(n / 1e7).toFixed(2)} Cr`
const fmtL  = (n: number) => `₹${(n / 1e5).toFixed(1)} L`
const fmtPct = (n: number) => `${(n * 100).toFixed(1)}%`

const STATUS_BADGE: Record<MSMEStatus, string> = {
  active: 'badge-success', inactive: 'badge-muted',
  npa: 'badge-danger', closed: 'badge-warning',
}

const NEED_LABELS: Record<string, string> = {
  working_capital: 'Working Capital',
  machinery_capex: 'Machinery/Capex',
  business_expansion: 'Business Expansion',
  inventory_funding: 'Inventory Funding',
  trade_finance: 'Trade Finance',
  digital_transformation: 'Digital Transformation',
}

const NEED_COLORS: Record<string, string> = {
  working_capital: '#4F6EF7',
  machinery_capex: '#7C3AED',
  business_expansion: '#10B981',
  inventory_funding: '#F59E0B',
  trade_finance: '#06B6D4',
  digital_transformation: '#EF4444',
}

const PRODUCT_LABELS: Record<string, string> = {
  cc_od: 'Cash Credit / Overdraft',
  machinery_term_loan: 'Machinery Term Loan',
  business_expansion_loan: 'Business Expansion Loan',
  inventory_funding: 'Inventory Funding Loan',
  trade_finance: 'Trade Finance',
  digital_business_loan: 'Digital Business Loan',
}

const STATUS_LABEL: Record<RecStatus, string> = {
  generated: 'Generated', sent: 'Sent', viewed: 'Viewed',
  applied: 'Applied', approved: 'Approved', rejected: 'Rejected',
}

// ── Sparkline ─────────────────────────────────────────────────────────
function GSTSparkline({ returns }: { returns: GSTReturn[] }) {
  const gstr3b = returns
    .filter(r => r.return_type === 'GSTR-3B')
    .sort((a, b) => a.tax_period.localeCompare(b.tax_period))
    .slice(-12)

  const data = gstr3b.map(r => ({
    period: r.tax_period.slice(0, 7),
    revenue: parseFloat((r.total_revenue / 1e5).toFixed(2)),
    liability: parseFloat((r.gst_liability / 1e5).toFixed(2)),
  }))

  if (data.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '32px 16px' }}>
        <TrendingUp size={24} />
        <p>No GST returns found</p>
      </div>
    )
  }

  const latest = data[data.length - 1]
  const prev   = data[data.length - 2]
  const growth = prev ? ((latest.revenue - prev.revenue) / prev.revenue) * 100 : 0

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>₹{latest.revenue.toLocaleString('en-IN')} L</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Latest Monthly Revenue</div>
        </div>
        <div className={`kpi-delta ${growth >= 0 ? 'positive' : 'negative'}`} style={{ fontSize: 14 }}>
          {growth >= 0 ? '↑' : '↓'} {Math.abs(growth).toFixed(1)}% MoM
        </div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: -30, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis dataKey="period" tick={{ fontSize: 9 }} tickLine={false} />
          <YAxis tick={{ fontSize: 10 }} tickLine={false} />
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Tooltip
            formatter={((v: any, name: any) => [`₹${v ?? 0}L`, name === 'revenue' ? 'Revenue' : 'GST Liability']) as any}
            labelFormatter={(l) => `Period: ${String(l)}`}
          />
          <Line type="monotone" dataKey="revenue" stroke="#4F6EF7" strokeWidth={2}
            dot={false} name="revenue" />
          <Line type="monotone" dataKey="liability" stroke="#F59E0B" strokeWidth={1.5}
            dot={false} name="liability" strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── AA Summary ────────────────────────────────────────────────────────
function AASummary({ accounts }: { accounts: AAAccount[] }) {
  const totalSanctioned = accounts.reduce((s, a) => s + a.sanctioned_limit, 0)
  const totalOutstanding = accounts.reduce((s, a) => s + a.outstanding_amount, 0)
  const totalOverdue = accounts.reduce((s, a) => s + a.overdue_amount, 0)
  const utilization = totalSanctioned > 0 ? totalOutstanding / totalSanctioned : 0
  const npaCount = accounts.filter(a => a.repayment_status === 'NPA').length
  const smaCount = accounts.filter(a => a.repayment_status.startsWith('SMA')).length

  const statusColor = npaCount > 0 ? 'var(--color-brand-danger)' :
                      smaCount > 0 ? 'var(--color-brand-warning)' : 'var(--color-brand-accent)'

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>{fmtPct(utilization)}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Credit Utilization</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: statusColor }}>
            {npaCount > 0 ? 'HIGH RISK' : smaCount > 0 ? 'STRESSED' : 'HEALTHY'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Credit Health</div>
        </div>
      </div>

      <div className="progress-bar" style={{ marginBottom: 16 }}>
        <div
          className="progress-fill"
          style={{
            width: `${Math.min(100, utilization * 100)}%`,
            background: utilization > 0.85
              ? 'var(--gradient-danger)'
              : utilization > 0.65
                ? 'linear-gradient(90deg, #F59E0B, #D97706)'
                : 'var(--gradient-brand)'
          }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        {[
          { label: 'Sanctioned', value: fmtCr(totalSanctioned) },
          { label: 'Outstanding', value: fmtCr(totalOutstanding) },
          { label: 'Overdue', value: fmtCr(totalOverdue) },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: 'var(--bg-elevated)',
            borderRadius: 8, padding: '10px 12px',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{value}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {accounts.length > 0 && (
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {accounts.map(a => (
            <div key={a.id} className="flex justify-between items-center" style={{
              padding: '8px 12px',
              background: 'var(--bg-elevated)',
              borderRadius: 8,
              fontSize: 12,
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>{a.fi_name}</span>
                <span className="badge badge-muted" style={{ marginLeft: 8 }}>{a.account_type}</span>
              </div>
              <div className="flex gap-sm items-center">
                <span style={{ color: 'var(--text-secondary)' }}>
                  {fmtCr(a.outstanding_amount)} / {fmtCr(a.sanctioned_limit)}
                </span>
                <span className={`badge ${
                  a.repayment_status === 'NPA' ? 'badge-danger' :
                  a.repayment_status.startsWith('SMA') ? 'badge-warning' : 'badge-success'
                }`}>{a.repayment_status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── SHAP Panel (XAI) ──────────────────────────────────────────────────
function SHAPPanel({ prediction }: { prediction: NeedPrediction }) {
  const shapData = Object.entries(prediction.shap_values)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 8)
    .map(([key, value]) => ({
      feature: key.replace(/_/g, ' '),
      value: parseFloat(value.toFixed(4)),
      positive: value >= 0,
    }))

  const needData = Object.entries(prediction.need_categories)
    .sort(([, a], [, b]) => b - a)
    .map(([cat, prob]) => ({
      name: NEED_LABELS[cat] ?? cat,
      probability: parseFloat((prob * 100).toFixed(1)),
      color: NEED_COLORS[cat] ?? '#4F6EF7',
      category: cat,
    }))

  return (
    <div>
      <div style={{
        background: `${NEED_COLORS[prediction.top_need] ?? '#4F6EF7'}18`,
        border: `1px solid ${NEED_COLORS[prediction.top_need] ?? '#4F6EF7'}40`,
        borderRadius: 12, padding: '12px 16px', marginBottom: 16,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Primary Need Detected
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: NEED_COLORS[prediction.top_need] ?? '#4F6EF7', marginTop: 4 }}>
            {NEED_LABELS[prediction.top_need] ?? prediction.top_need}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{fmtPct(prediction.confidence_score)}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Confidence</div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>
          All Need Probabilities
        </div>
        {needData.map(({ name, probability, color, category }) => (
          <div key={category} style={{ marginBottom: 8 }}>
            <div className="flex justify-between" style={{ marginBottom: 4 }}>
              <span style={{ fontSize: 12 }}>{name}</span>
              <span className="font-mono" style={{ fontSize: 12, fontWeight: 600 }}>{probability}%</span>
            </div>
            <div className="progress-bar">
              <div style={{
                width: `${probability}%`, height: '100%', borderRadius: '999px',
                background: color, transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
              }} />
            </div>
          </div>
        ))}
      </div>

      <div>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>
          XAI · Top Feature Drivers (SHAP)
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart layout="vertical" data={shapData} margin={{ top: 0, right: 10, left: 80, bottom: 0 }}>
            <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} />
            <YAxis type="category" dataKey="feature" tick={{ fontSize: 10 }} width={80} />
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <Tooltip formatter={((v: any) => [`${v ?? 0}`, 'SHAP value']) as any} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {shapData.map((entry, idx) => (
                <Cell key={idx} fill={entry.positive ? '#10B981' : '#EF4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-md" style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#10B981' }} />
            Positive driver
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#EF4444' }} />
            Negative driver
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Product Recommendation Card ───────────────────────────────────────
function RecommendationCard({ rec }: { rec: ProductRecommendation }) {
  const qc = useQueryClient()
  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: RecStatus }) =>
      updateRecommendationStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['msme'] }),
  })

  const nextStatus: Partial<Record<RecStatus, RecStatus>> = {
    generated: 'sent', sent: 'viewed', viewed: 'applied', applied: 'approved',
  }

  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
      borderRadius: 12, padding: '16px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: 12, right: 12,
        background: 'var(--gradient-brand)', color: 'white', borderRadius: '50%',
        width: 28, height: 28, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 12, fontWeight: 800,
      }}>
        #{rec.rank}
      </div>

      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, paddingRight: 36 }}>
        {PRODUCT_LABELS[rec.product_type] ?? rec.product_type}
      </div>

      <span className={`status-pill status-${rec.status}`}>{STATUS_LABEL[rec.status]}</span>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
        {[
          { label: 'Amount', value: fmtL(rec.suggested_amount) },
          { label: 'Tenure', value: `${rec.suggested_tenure_months}m` },
          { label: 'Rate', value: `${rec.suggested_rate.toFixed(1)}% p.a.` },
        ].map(({ label, value }) => (
          <div key={label} style={{ textAlign: 'center', background: 'var(--bg-surface)', borderRadius: 6, padding: '6px 4px' }}>
            <div style={{ fontSize: 12, fontWeight: 700 }}>{value}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</div>
          </div>
        ))}
      </div>

      <div className="flex justify-between" style={{ marginTop: 12 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>Eligibility</div>
          <div className="progress-bar" style={{ width: 80 }}>
            <div className="progress-fill brand" style={{ width: `${rec.eligibility_score * 100}%` }} />
          </div>
          <div style={{ fontSize: 10, marginTop: 2 }}>{fmtPct(rec.eligibility_score)}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>Ranking</div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{(rec.ranking_score * 100).toFixed(0)}/100</div>
        </div>
      </div>

      {rec.eligibility_rules_passed.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {rec.eligibility_rules_passed.slice(0, 2).map(r => (
            <div key={r} className="flex gap-xs items-center" style={{ fontSize: 10, color: 'var(--color-brand-accent)', marginBottom: 2 }}>
              <CheckCircle size={10} /> {r}
            </div>
          ))}
          {rec.eligibility_rules_failed.slice(0, 1).map(r => (
            <div key={r} className="flex gap-xs items-center" style={{ fontSize: 10, color: 'var(--color-brand-danger)', marginBottom: 2 }}>
              <XCircle size={10} /> {r}
            </div>
          ))}
        </div>
      )}

      {rec.status !== 'approved' && rec.status !== 'rejected' && (
        <div className="flex gap-sm" style={{ marginTop: 12 }}>
          {nextStatus[rec.status] && (
            <button
              className="btn btn-primary btn-sm"
              style={{ flex: 1, fontSize: 11 }}
              onClick={() => mutation.mutate({ id: rec.id, status: nextStatus[rec.status]! })}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? <RefreshCw size={12} /> : <CheckCircle size={12} />}
              Mark {STATUS_LABEL[nextStatus[rec.status]!]}
            </button>
          )}
          <button
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11 }}
            onClick={() => mutation.mutate({ id: rec.id, status: 'rejected' })}
            disabled={mutation.isPending}
          >
            <XCircle size={12} /> Reject
          </button>
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────
export function MSMEProfilePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery<FullMSMEProfile>({
    queryKey: ['msme', id],
    queryFn: () => fetchMSMEById(id!),
    enabled: !!id,
    retry: 1,
  })

  const { data: eligibilityData } = useQuery({
    queryKey: ['eligibility', id],
    queryFn: () => fetchLoanExplanationGet(id!, 2500000),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="page-container">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', flexDirection: 'column', gap: 16 }}>
          <div className="spinner" style={{ width: 36, height: 36 }} />
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading MSME profile…</div>
        </div>
      </div>
    )
  }

  if (error || !data?.msme) {
    return (
      <div className="page-container">
        <div className="empty-state" style={{ minHeight: '50vh' }}>
          <AlertTriangle size={40} />
          <p>MSME not found or backend is offline.</p>
          <button className="btn btn-secondary" onClick={() => navigate('/msmes')}>
            <ArrowLeft size={14} /> Back to Directory
          </button>
        </div>
      </div>
    )
  }

  const { msme, gst_returns, aa_accounts, latest_need_prediction, product_recommendations } = data

  const incYears = msme.incorporation_date
    ? Math.floor((Date.now() - new Date(msme.incorporation_date).getTime()) / (365.25 * 24 * 3600 * 1000))
    : null

  return (
    <div className="page-container fade-in">
      <button className="btn btn-ghost btn-sm mb-lg" onClick={() => navigate('/msmes')}>
        <ArrowLeft size={14} /> Back to Directory
      </button>

      {/* Business identity card */}
      <div className="card mb-lg">
        <div className="card-body">
          <div className="flex justify-between items-start">
            <div className="flex gap-md items-start">
              <div style={{
                width: 56, height: 56, borderRadius: 14,
                background: 'var(--gradient-brand)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, fontWeight: 800, color: 'white', flexShrink: 0,
              }}>
                {msme.legal_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>{msme.legal_name}</h2>
                {msme.trade_name && msme.trade_name !== msme.legal_name && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
                    Trade name: {msme.trade_name}
                  </div>
                )}
                <div className="flex gap-sm" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
                  <span className={`badge ${STATUS_BADGE[msme.status]}`}>{msme.status}</span>
                  {msme.constitution && <span className="badge badge-muted">{msme.constitution}</span>}
                  {msme.nic_code && <span className="badge badge-info">NIC: {msme.nic_code}</span>}
                  {msme.behavioral_tag && (
                    <span className="badge" style={{
                      background: msme.behavioral_tag === 'Disciplined Spender' ? 'rgba(16,185,129,0.15)' :
                                  msme.behavioral_tag === 'High Cash Burn' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                      color: msme.behavioral_tag === 'Disciplined Spender' ? '#10b981' :
                             msme.behavioral_tag === 'High Cash Burn' ? '#f87171' : '#f59e0b',
                      fontWeight: 700
                    }}>
                      ⚡ {msme.behavioral_tag}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="font-mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{msme.gstin}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>PAN: {msme.pan}</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 16 }}>
            {[
              { icon: <MapPin size={13} />, label: 'Location', value: [msme.city, msme.state].filter(Boolean).join(', ') || '—' },
              { icon: <Calendar size={13} />, label: 'Age', value: incYears ? `${incYears} years` : '—' },
              { icon: <Building2 size={13} />, label: 'NIC Sector', value: msme.nic_description?.slice(0, 35) ?? '—' },
              { icon: <Shield size={13} />, label: 'GST Reg.', value: msme.gst_registration_date ? new Date(msme.gst_registration_date).getFullYear().toString() : '—' },
              { icon: <Zap size={13} />, label: 'EPFO Active Employees', value: msme.epfo_active_employees !== undefined ? `${msme.epfo_active_employees} employees` : '—' },
              { icon: <RefreshCw size={13} />, label: 'PF Compliance Score', value: msme.pf_compliance_score !== undefined ? `${msme.pf_compliance_score}%` : '—' },
            ].map(({ icon, label, value }) => (
              <div key={label} style={{ background: 'var(--bg-elevated)', borderRadius: 8, padding: '10px 12px' }}>
                <div className="flex gap-xs items-center" style={{ color: 'var(--text-muted)', fontSize: 10, marginBottom: 4 }}>
                  {icon} {label}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid-21 mb-lg">
        <div className="flex-col gap-lg">
          <div className="card">
            <div className="card-header">
              <span className="card-title">12-Month GST Revenue Trend</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{gst_returns.length} returns</span>
            </div>
            <div className="card-body">
              <GSTSparkline returns={gst_returns} />
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Account Aggregator — Liability</span>
              <span className="badge badge-brand">{aa_accounts.length} accounts</span>
            </div>
            <div className="card-body">
              {aa_accounts.length === 0 ? (
                <div className="empty-state" style={{ padding: '20px' }}>
                  <CreditCard size={24} />
                  <p>No AA accounts linked</p>
                </div>
              ) : (
                <AASummary accounts={aa_accounts} />
              )}
            </div>
          </div>

          {/* Repayment Capacity & Alternate Cash Flow Analysis Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Repayment Capacity & Alternate Cash Flow Analysis</span>
            </div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 20 }}>
                {/* Left: Repayment Capacity Widget */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, justifyContent: 'center' }}>
                  <div style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.15)', borderRadius: 12, padding: 16 }}>
                    <div style={{ fontSize: 11, color: '#67e8f9', fontWeight: 600, textTransform: 'uppercase' }}>Disposable Income (Monthly)</div>
                    <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>
                      {msme.disposable_income ? `₹${(msme.disposable_income / 1e5).toFixed(2)} Lakh` : '—'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: 12, padding: 16 }}>
                    <div style={{ fontSize: 11, color: '#6ee7b7', fontWeight: 600, textTransform: 'uppercase' }}>Max EMI Capacity (50%)</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#10b981', marginTop: 4 }}>
                      {msme.disposable_income ? `₹${((msme.disposable_income * 0.5) / 1e5).toFixed(2)} Lakh` : '—'}/mo
                    </div>
                  </div>
                </div>

                {/* Right: Bar chart of GST revenue vs AA cash outflows */}
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8, fontWeight: 600 }}>
                    GST Revenue vs Cash Outflow vs Cash Inflow
                  </div>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={[
                      { name: 'Avg GST Rev', Amount: parseFloat((gst_returns.reduce((s, r) => s + r.total_revenue, 0) / (gst_returns.length || 1) / 1e5).toFixed(2)), fill: '#4F6EF7' },
                      { name: 'Bank Inflow', Amount: parseFloat(((msme.avg_monthly_inflow ?? 0) / 1e5).toFixed(2)), fill: '#10B981' },
                      { name: 'Bank Outflow', Amount: parseFloat(((msme.avg_monthly_outflow ?? 0) / 1e5).toFixed(2)), fill: '#EF4444' },
                    ]} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                      <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v) => [`₹${v} L`, 'Amount']} />
                      <Bar dataKey="Amount" radius={[4, 4, 0, 0]}>
                        <Cell fill="#4F6EF7" />
                        <Cell fill="#10B981" />
                        <Cell fill="#EF4444" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-col gap-lg">
          <div className="card">
            <div className="card-header">
              <span className="card-title">AI Need Detection + XAI</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {latest_need_prediction?.model_version ?? '—'}
              </span>
            </div>
            <div className="card-body">
              {latest_need_prediction ? (
                <SHAPPanel prediction={latest_need_prediction} />
              ) : (
                <div className="empty-state" style={{ padding: '32px 16px' }}>
                  <Zap size={28} />
                  <p>No need prediction yet.</p>
                  <button className="btn btn-primary btn-sm" style={{ marginTop: 8 }}>
                    <Zap size={13} /> Run Prediction
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* AI Underwriter Memo Card */}
          {eligibilityData && (
            <div className="card">
              <div className="card-header flex justify-between items-center">
                <span className="card-title flex gap-xs items-center">
                  <FileText size={16} color="#6366f1" /> AI Underwriter Memo
                </span>
                {eligibilityData.narrative_source && (
                  <span style={{
                    padding: '3px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                    background: eligibilityData.narrative_source.startsWith('llm') || eligibilityData.narrative_source.includes('gemini') ? 'rgba(16,185,129,0.15)' : 'rgba(99,102,241,0.15)',
                    color: eligibilityData.narrative_source.startsWith('llm') || eligibilityData.narrative_source.includes('gemini') ? '#10b981' : '#6366f1'
                  }}>
                    {eligibilityData.narrative_source.toUpperCase().replace('_', ' ')}
                  </span>
                )}
              </div>
              <div className="card-body">
                <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}
                  dangerouslySetInnerHTML={{ __html: eligibilityData.executive_summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                />
                {eligibilityData.risk_summary && (
                  <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 600 }}>
                      Risk Assessment
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}
                      dangerouslySetInnerHTML={{ __html: eligibilityData.risk_summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Product Recommendations */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Product Recommendations</span>
          <span className="badge badge-brand">{product_recommendations.length} products</span>
        </div>
        <div className="card-body">
          {product_recommendations.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px' }}>
              <Target size={28} />
              <p>No recommendations generated yet for this MSME.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              {product_recommendations
                .sort((a, b) => a.rank - b.rank)
                .map(rec => (
                  <RecommendationCard key={rec.id} rec={rec} />
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
