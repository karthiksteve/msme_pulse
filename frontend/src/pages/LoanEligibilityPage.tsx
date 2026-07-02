import { useState, useRef } from 'react'
import {
  Shield, TrendingUp, AlertTriangle, CheckCircle, XCircle,
  ChevronDown, ChevronUp, Zap, ArrowRight, Star, Info,
  BarChart2, Award, Target, FileText, RefreshCw, HelpCircle
} from 'lucide-react'
import { fetchLoanExplanation, type XAILoanRequest } from '../api/client'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScoreSlabRow {
  metric_name: string
  description: string
  your_value: string
  healthy_min: string
  healthy_max: string
  status: 'HEALTHY' | 'CAUTION' | 'CRITICAL'
  impact_on_score: string
  improvement_tip: string
}

interface FeatureContribution {
  feature_name: string
  display_name: string
  value: string
  contribution_score: number
  direction: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
  explanation: string
}

interface LoanProductSuggestion {
  product_name: string
  product_type: string
  suggested_amount: number
  suggested_amount_label: string
  suggested_tenure_months: number
  suggested_rate: number
  emi_estimate: number
  rationale: string
}

interface XAIResponse {
  msme_id: string
  legal_name: string
  gstin: string
  eligibility_score: number
  eligibility_band: string
  eligibility_label: string
  is_eligible: boolean
  computed_max_loan_amount: number
  computed_max_loan_label: string
  asking_amount: number
  asking_amount_label: string
  asking_vs_computed_pct: number
  higher_amount_eligible: boolean
  higher_amount_suggestion: number | null
  higher_amount_label: string | null
  higher_amount_rationale: string | null
  loan_suggestions: LoanProductSuggestion[]
  executive_summary: string
  score_breakdown_narrative: string
  risk_summary: string
  score_slab: ScoreSlabRow[]
  feature_contributions: FeatureContribution[]
  areas_of_improvement: string[]
  strengths: string[]
  sub_scores: Record<string, number>
  sub_score_labels: Record<string, string>
  data_completeness_pct: number
  data_sources_used: string[]
  as_of_date: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BAND_COLORS: Record<string, { gradient: string; glow: string; text: string; badge: string }> = {
  EXCELLENT: {
    gradient: 'linear-gradient(135deg, #10b981, #059669)',
    glow: '0 0 40px rgba(16,185,129,0.4)',
    text: '#10b981',
    badge: '#d1fae5',
  },
  GOOD: {
    gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    glow: '0 0 40px rgba(59,130,246,0.4)',
    text: '#3b82f6',
    badge: '#dbeafe',
  },
  FAIR: {
    gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
    glow: '0 0 40px rgba(245,158,11,0.4)',
    text: '#f59e0b',
    badge: '#fef3c7',
  },
  POOR: {
    gradient: 'linear-gradient(135deg, #f97316, #ea580c)',
    glow: '0 0 40px rgba(249,115,22,0.4)',
    text: '#f97316',
    badge: '#ffedd5',
  },
  INELIGIBLE: {
    gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
    glow: '0 0 40px rgba(239,68,68,0.4)',
    text: '#ef4444',
    badge: '#fee2e2',
  },
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  HEALTHY: <CheckCircle size={16} style={{ color: '#10b981' }} />,
  CAUTION: <AlertTriangle size={16} style={{ color: '#f59e0b' }} />,
  CRITICAL: <XCircle size={16} style={{ color: '#ef4444' }} />,
}

const STATUS_COLOR: Record<string, string> = {
  HEALTHY: '#10b981',
  CAUTION: '#f59e0b',
  CRITICAL: '#ef4444',
}

const PRODUCT_TYPE_COLORS: Record<string, string> = {
  cc_od: 'linear-gradient(135deg, #6366f1, #4f46e5)',
  machinery_term_loan: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
  business_expansion_loan: 'linear-gradient(135deg, #10b981, #059669)',
  inventory_funding: 'linear-gradient(135deg, #f59e0b, #d97706)',
  digital_business_loan: 'linear-gradient(135deg, #a855f7, #9333ea)',
}

function fmtINR(v: number): string {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)} L`
  return `₹${v.toLocaleString('en-IN')}`
}

function fmtEMI(v: number): string {
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L/mo`
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K/mo`
  return `₹${Math.round(v)}/mo`
}

// ─── Score Gauge ──────────────────────────────────────────────────────────────

function ScoreGauge({ score, band }: { score: number; band: string }) {
  const colors = BAND_COLORS[band] || BAND_COLORS.FAIR
  const radius = 90
  const circumference = Math.PI * radius  // half circle
  const progress = (score / 100) * circumference

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width="220" height="120" viewBox="0 0 220 120">
        {/* Background arc */}
        <path
          d={`M15,110 A${radius},${radius} 0 0,1 205,110`}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="16"
          strokeLinecap="round"
        />
        {/* Progress arc */}
        <path
          d={`M15,110 A${radius},${radius} 0 0,1 205,110`}
          fill="none"
          stroke="url(#gaugeGrad)"
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(0.4,0,0.2,1)' }}
        />
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={colors.text} stopOpacity="0.7" />
            <stop offset="100%" stopColor={colors.text} />
          </linearGradient>
        </defs>
        {/* Tick marks */}
        {[0, 25, 50, 75, 100].map((tick) => {
          const angle = (tick / 100) * 180 - 180  // -180 to 0
          const rad = (angle * Math.PI) / 180
          const x = 110 + radius * Math.cos(rad)
          const y = 110 + radius * Math.sin(rad)
          return (
            <text
              key={tick}
              x={x}
              y={y - 4}
              textAnchor="middle"
              fontSize="9"
              fill="rgba(255,255,255,0.4)"
            >
              {tick}
            </text>
          )
        })}
        {/* Score value */}
        <text x="110" y="98" textAnchor="middle" fontSize="36" fontWeight="700" fill="white">
          {Math.round(score)}
        </text>
        <text x="110" y="115" textAnchor="middle" fontSize="11" fill="rgba(255,255,255,0.5)">
          / 100
        </text>
      </svg>
    </div>
  )
}

// ─── Sub Score Radar ──────────────────────────────────────────────────────────

function SubScoreRadar({ subScores, labels }: { subScores: Record<string, number>; labels: Record<string, string> }) {
  const keys = Object.keys(subScores)
  const n = keys.length
  const cx = 140, cy = 140, r = 110

  const points = keys.map((_, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2
    const val = (subScores[keys[i]] / 100) * r
    return {
      x: cx + val * Math.cos(angle),
      y: cy + val * Math.sin(angle),
      lx: cx + (r + 28) * Math.cos(angle),
      ly: cy + (r + 28) * Math.sin(angle),
    }
  })

  const polygon = points.map(p => `${p.x},${p.y}`).join(' ')

  const gridPolygons = [20, 40, 60, 80, 100].map(pct => {
    const pts = keys.map((_, i) => {
      const angle = (i / n) * 2 * Math.PI - Math.PI / 2
      const val = (pct / 100) * r
      return `${cx + val * Math.cos(angle)},${cy + val * Math.sin(angle)}`
    })
    return pts.join(' ')
  })

  return (
    <svg width="280" height="280" viewBox="0 0 280 280">
      {/* Grid rings */}
      {gridPolygons.map((pts, i) => (
        <polygon
          key={i}
          points={pts}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="1"
        />
      ))}
      {/* Axis lines */}
      {keys.map((_, i) => {
        const angle = (i / n) * 2 * Math.PI - Math.PI / 2
        return (
          <line
            key={i}
            x1={cx} y1={cy}
            x2={cx + r * Math.cos(angle)}
            y2={cy + r * Math.sin(angle)}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="1"
          />
        )
      })}
      {/* Data polygon */}
      <polygon
        points={polygon}
        fill="rgba(99,102,241,0.25)"
        stroke="#6366f1"
        strokeWidth="2"
      />
      {/* Data points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="#6366f1" />
      ))}
      {/* Labels */}
      {points.map((p, i) => (
        <text
          key={i}
          x={p.lx}
          y={p.ly}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="9"
          fill="rgba(255,255,255,0.6)"
        >
          {labels[keys[i]] || keys[i]}
        </text>
      ))}
      {/* Score values */}
      {points.map((p, i) => {
        const angle = (i / n) * 2 * Math.PI - Math.PI / 2
        const vx = cx + ((subScores[keys[i]] / 100) * r * 0.5) * Math.cos(angle)
        const vy = cy + ((subScores[keys[i]] / 100) * r * 0.5) * Math.sin(angle)
        return (
          <text key={i} x={vx} y={vy} textAnchor="middle" dominantBaseline="middle" fontSize="8" fill="white" fontWeight="600">
            {Math.round(subScores[keys[i]])}
          </text>
        )
      })}
    </svg>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function LoanEligibilityPage() {
  const [msmeId, setMsmeId] = useState('')
  const [askingAmount, setAskingAmount] = useState('')
  const [loanPurpose, setLoanPurpose] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<XAIResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedSlab, setExpandedSlab] = useState<number | null>(null)
  const [expandedContrib, setExpandedContrib] = useState<number | null>(null)
  const resultRef = useRef<HTMLDivElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!msmeId.trim() || !askingAmount) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload: XAILoanRequest = {
        msme_id: msmeId.trim(),
        asking_amount: parseFloat(askingAmount) * 100_000,  // input in Lakhs
        loan_purpose: loanPurpose || undefined,
      }
      const data = await fetchLoanExplanation(payload)
      setResult(data)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to fetch explanation'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const band = result ? BAND_COLORS[result.eligibility_band] || BAND_COLORS.FAIR : null

  return (
    <div style={{ padding: '24px', maxWidth: 1300, margin: '0 auto' }}>

      {/* ─── Page Header ─────────────────────────────────────────────── */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(99,102,241,0.4)'
          }}>
            <Shield size={22} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              XAI Loan Eligibility Engine
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
              Explainable AI — Multidimensional MSME Financial Health Assessment
            </p>
          </div>
        </div>
        <div style={{
          display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12
        }}>
          {['GST Compliance', 'Revenue Health', 'Repayment Behavior', 'Credit Utilization', 'Business Stability'].map(tag => (
            <span key={tag} style={{
              padding: '4px 10px', borderRadius: 20,
              background: 'rgba(99,102,241,0.1)',
              border: '1px solid rgba(99,102,241,0.2)',
              fontSize: 11, color: '#a5b4fc', fontWeight: 500
            }}>{tag}</span>
          ))}
        </div>
      </div>

      {/* ─── Input Form ───────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} style={{
        background: 'var(--surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 16,
        padding: 24,
        marginBottom: 32,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr auto',
        gap: 16,
        alignItems: 'end'
      }}>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            MSME ID (UUID)
          </label>
          <input
            id="xai-msme-id"
            type="text"
            value={msmeId}
            onChange={e => setMsmeId(e.target.value)}
            placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
            required
            style={{
              width: '100%', padding: '10px 14px',
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)',
              fontSize: 14, fontFamily: 'monospace',
              boxSizing: 'border-box'
            }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Loan Amount Asking (₹ Lakhs)
          </label>
          <input
            id="xai-asking-amount"
            type="number"
            min="1"
            step="0.5"
            value={askingAmount}
            onChange={e => setAskingAmount(e.target.value)}
            placeholder="e.g. 25"
            required
            style={{
              width: '100%', padding: '10px 14px',
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)',
              fontSize: 14, boxSizing: 'border-box'
            }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Loan Purpose (Optional)
          </label>
          <select
            id="xai-loan-purpose"
            value={loanPurpose}
            onChange={e => setLoanPurpose(e.target.value)}
            style={{
              width: '100%', padding: '10px 14px',
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)',
              fontSize: 14, boxSizing: 'border-box'
            }}
          >
            <option value="">— Select Purpose —</option>
            <option value="working_capital">Working Capital</option>
            <option value="machinery">Machinery / Equipment</option>
            <option value="expansion">Business Expansion</option>
            <option value="inventory">Inventory Funding</option>
            <option value="digital">Digital Transformation</option>
          </select>
        </div>
        <button
          type="submit"
          id="xai-submit-btn"
          disabled={loading}
          style={{
            padding: '10px 28px',
            background: loading ? 'rgba(99,102,241,0.4)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none', borderRadius: 8,
            color: 'white', fontWeight: 600, fontSize: 14,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 8,
            whiteSpace: 'nowrap',
            boxShadow: loading ? 'none' : '0 4px 20px rgba(99,102,241,0.4)',
            transition: 'all 0.2s'
          }}
        >
          {loading ? <><RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} /> Analyzing…</> : <><Zap size={16} /> Analyze Now</>}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div style={{
          padding: '14px 18px', borderRadius: 10, marginBottom: 24,
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          color: '#f87171', fontSize: 14
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* ─── Result ───────────────────────────────────────────────────── */}
      {result && (
        <div ref={resultRef} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* ─ Row 1: Score Card + Radar ──── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>

            {/* Eligibility Score Card */}
            <div style={{
              gridColumn: '1 / 2',
              background: band!.gradient,
              borderRadius: 20, padding: 28,
              boxShadow: band!.glow,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              position: 'relative', overflow: 'hidden'
            }}>
              <div style={{
                position: 'absolute', top: -20, right: -20,
                width: 120, height: 120, borderRadius: '50%',
                background: 'rgba(255,255,255,0.07)'
              }} />
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                Eligibility Score
              </div>
              <ScoreGauge score={result.eligibility_score} band={result.eligibility_band} />
              <div style={{
                marginTop: 4, padding: '6px 18px', borderRadius: 20,
                background: 'rgba(255,255,255,0.2)',
                fontSize: 13, fontWeight: 700, color: 'white', letterSpacing: '0.05em'
              }}>
                {result.eligibility_band}
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.8)', textAlign: 'center' }}>
                {result.eligibility_label}
              </div>
              <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                {result.is_eligible
                  ? <CheckCircle size={18} color="white" />
                  : <XCircle size={18} color="rgba(255,255,255,0.6)" />}
                <span style={{ color: 'white', fontWeight: 600, fontSize: 13 }}>
                  {result.is_eligible ? 'ELIGIBLE FOR LOAN' : 'NOT CURRENTLY ELIGIBLE'}
                </span>
              </div>
            </div>

            {/* Loan Amounts Panel */}
            <div style={{
              background: 'var(--surface)', borderRadius: 20,
              border: '1px solid var(--border-subtle)', padding: 24,
              display: 'flex', flexDirection: 'column', gap: 16
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Loan Amount Analysis
              </div>

              {/* Asking vs Computed */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{
                  padding: '14px 16px', borderRadius: 12,
                  background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)'
                }}>
                  <div style={{ fontSize: 11, color: '#a5b4fc', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>You Are Asking</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: 'white' }}>{result.asking_amount_label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {result.asking_vs_computed_pct.toFixed(1)}% of your computed maximum
                  </div>
                </div>
                <div style={{
                  padding: '14px 16px', borderRadius: 12,
                  background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)'
                }}>
                  <div style={{ fontSize: 11, color: '#6ee7b7', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>We Computed (Max Eligible)</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#10b981' }}>{result.computed_max_loan_label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    Based on GST turnover × eligibility score multiplier
                  </div>
                </div>
              </div>

              {/* Progress bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                  <span>Asking / Maximum</span>
                  <span>{Math.min(result.asking_vs_computed_pct, 100).toFixed(1)}%</span>
                </div>
                <div style={{ height: 8, borderRadius: 4, background: 'var(--surface-raised)', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(result.asking_vs_computed_pct, 100)}%`,
                    background: result.asking_vs_computed_pct > 100
                      ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                      : 'linear-gradient(90deg, #6366f1, #10b981)',
                    borderRadius: 4,
                    transition: 'width 1s ease'
                  }} />
                </div>
              </div>
            </div>

            {/* Spider Chart */}
            <div style={{
              background: 'var(--surface)', borderRadius: 20,
              border: '1px solid var(--border-subtle)', padding: 20,
              display: 'flex', flexDirection: 'column', alignItems: 'center'
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8, alignSelf: 'flex-start' }}>
                Score Profile
              </div>
              <SubScoreRadar subScores={result.sub_scores} labels={result.sub_score_labels} />
            </div>
          </div>

          {/* ─ Higher Amount Banner ──── */}
          {result.higher_amount_eligible && result.higher_amount_suggestion && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(6,182,212,0.12))',
              border: '1px solid rgba(16,185,129,0.35)',
              borderRadius: 16, padding: '20px 24px',
              display: 'flex', alignItems: 'flex-start', gap: 16
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 16px rgba(16,185,129,0.4)'
              }}>
                <Star size={20} color="white" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#10b981', marginBottom: 4 }}>
                  🚀 Premium Offer: You Qualify for {result.higher_amount_label}!
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {result.higher_amount_rationale}
                </div>
              </div>
              <div style={{
                padding: '8px 16px', borderRadius: 8, flexShrink: 0,
                background: 'rgba(16,185,129,0.15)',
                border: '1px solid rgba(16,185,129,0.3)',
                fontSize: 22, fontWeight: 800, color: '#10b981'
              }}>
                {result.higher_amount_label}
              </div>
            </div>
          )}

          {/* ─ Row 2: XAI Narratives ──── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div style={{
              background: 'var(--surface)', borderRadius: 16,
              border: '1px solid var(--border-subtle)', padding: 22
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <FileText size={16} color="#6366f1" />
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Executive Summary</span>
              </div>
              <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7 }}
                dangerouslySetInnerHTML={{ __html: result.executive_summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
              />
            </div>
            <div style={{
              background: 'var(--surface)', borderRadius: 16,
              border: '1px solid var(--border-subtle)', padding: 22
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <AlertTriangle size={16} color={result.is_eligible ? '#10b981' : '#ef4444'} />
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Risk Summary</span>
              </div>
              <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7 }}
                dangerouslySetInnerHTML={{ __html: result.risk_summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
              />
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', fontSize: 12, color: 'var(--text-muted)' }}>
                {result.score_breakdown_narrative.replace(/\*\*(.*?)\*\*/g, '$1')}
              </div>
            </div>
          </div>

          {/* ─ Score Slab Comparison Table ──── */}
          <div style={{
            background: 'var(--surface)', borderRadius: 20,
            border: '1px solid var(--border-subtle)', overflow: 'hidden'
          }}>
            <div style={{
              padding: '18px 24px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', gap: 10,
              background: 'linear-gradient(90deg, rgba(99,102,241,0.06), transparent)'
            }}>
              <BarChart2 size={18} color="#6366f1" />
              <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                Healthy Score Slab — Your Metrics vs Benchmark
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                Click a row for improvement tips
              </span>
            </div>

            {/* Table header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '22px 2fr 1fr 1fr 1fr 80px 80px',
              gap: 0,
              padding: '10px 24px',
              background: 'var(--surface-raised)',
              borderBottom: '1px solid var(--border-subtle)',
              fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
              textTransform: 'uppercase', letterSpacing: '0.05em'
            }}>
              <div />
              <div>Metric</div>
              <div style={{ textAlign: 'center' }}>Your Value</div>
              <div style={{ textAlign: 'center' }}>Healthy Min</div>
              <div style={{ textAlign: 'center' }}>Healthy Max</div>
              <div style={{ textAlign: 'center' }}>Status</div>
              <div style={{ textAlign: 'center' }}>Impact</div>
            </div>

            {result.score_slab.map((row, i) => (
              <div key={i}>
                <div
                  onClick={() => setExpandedSlab(expandedSlab === i ? null : i)}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '22px 2fr 1fr 1fr 1fr 80px 80px',
                    gap: 0,
                    padding: '14px 24px',
                    borderBottom: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                    background: expandedSlab === i ? 'rgba(99,102,241,0.05)' : 'transparent',
                    alignItems: 'center'
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                  onMouseLeave={e => (e.currentTarget.style.background = expandedSlab === i ? 'rgba(99,102,241,0.05)' : 'transparent')}
                >
                  <div>{STATUS_ICON[row.status]}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{row.metric_name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{row.description}</div>
                  </div>
                  <div style={{ textAlign: 'center', fontSize: 14, fontWeight: 700, color: STATUS_COLOR[row.status] }}>
                    {row.your_value}
                  </div>
                  <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>{row.healthy_min}</div>
                  <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>{row.healthy_max}</div>
                  <div style={{ textAlign: 'center' }}>
                    <span style={{
                      padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                      background: row.status === 'HEALTHY' ? 'rgba(16,185,129,0.15)' : row.status === 'CAUTION' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                      color: STATUS_COLOR[row.status]
                    }}>
                      {row.status}
                    </span>
                  </div>
                  <div style={{ textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                    <span style={{
                      fontSize: 12, fontWeight: 700,
                      color: row.impact_on_score.startsWith('+') ? '#10b981' : '#f87171'
                    }}>
                      {row.impact_on_score}
                    </span>
                    {expandedSlab === i ? <ChevronUp size={14} color="var(--text-muted)" /> : <ChevronDown size={14} color="var(--text-muted)" />}
                  </div>
                </div>

                {/* Expanded improvement tip */}
                {expandedSlab === i && (
                  <div style={{
                    padding: '12px 24px 16px',
                    background: 'rgba(99,102,241,0.05)',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex', alignItems: 'flex-start', gap: 10
                  }}>
                    <HelpCircle size={16} color="#6366f1" style={{ marginTop: 2, flexShrink: 0 }} />
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      <strong style={{ color: '#a5b4fc' }}>💡 Improvement Tip: </strong>
                      {row.improvement_tip}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* ─ Feature Contributions (XAI) ──── */}
          <div style={{
            background: 'var(--surface)', borderRadius: 20,
            border: '1px solid var(--border-subtle)', overflow: 'hidden'
          }}>
            <div style={{
              padding: '18px 24px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', gap: 10,
              background: 'linear-gradient(90deg, rgba(16,185,129,0.06), transparent)'
            }}>
              <Zap size={18} color="#10b981" />
              <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                Explainable AI — What's Driving Your Score?
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                SHAP-style feature contributions
              </span>
            </div>
            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {result.feature_contributions.map((fc, i) => {
                const isPos = fc.direction === 'POSITIVE'
                const isNeg = fc.direction === 'NEGATIVE'
                const absVal = Math.abs(fc.contribution_score)
                const maxContrib = 20
                const widthPct = Math.min(absVal / maxContrib * 100, 100)

                return (
                  <div key={i}>
                    <div
                      onClick={() => setExpandedContrib(expandedContrib === i ? null : i)}
                      style={{
                        display: 'grid', gridTemplateColumns: '180px 1fr 60px 30px',
                        gap: 12, alignItems: 'center', cursor: 'pointer', padding: '8px 4px',
                        borderRadius: 8,
                        transition: 'background 0.15s'
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{fc.display_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fc.value}</div>
                      </div>

                      {/* Diverging bar */}
                      <div style={{ position: 'relative', height: 24, borderRadius: 6, background: 'var(--surface-raised)', overflow: 'hidden' }}>
                        <div style={{
                          position: 'absolute',
                          top: 0, height: '100%',
                          width: `${widthPct / 2}%`,
                          left: isPos ? '50%' : undefined,
                          right: isNeg ? '50%' : undefined,
                          background: isPos
                            ? 'linear-gradient(90deg, rgba(16,185,129,0.6), #10b981)'
                            : 'linear-gradient(90deg, #ef4444, rgba(239,68,68,0.6))',
                          borderRadius: isPos ? '0 4px 4px 0' : '4px 0 0 4px',
                          transition: 'width 0.8s ease'
                        }} />
                        {/* Center line */}
                        <div style={{
                          position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1,
                          background: 'rgba(255,255,255,0.15)'
                        }} />
                      </div>

                      <div style={{
                        fontSize: 13, fontWeight: 700, textAlign: 'right',
                        color: isPos ? '#10b981' : isNeg ? '#f87171' : 'var(--text-muted)'
                      }}>
                        {fc.contribution_score > 0 ? '+' : ''}{fc.contribution_score.toFixed(1)}
                      </div>
                      <div>
                        {expandedContrib === i
                          ? <ChevronUp size={14} color="var(--text-muted)" />
                          : <ChevronDown size={14} color="var(--text-muted)" />}
                      </div>
                    </div>

                    {expandedContrib === i && (
                      <div style={{
                        margin: '4px 0 8px', padding: '12px 16px',
                        background: 'rgba(99,102,241,0.06)', borderRadius: 8,
                        fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
                        borderLeft: `3px solid ${isPos ? '#10b981' : isNeg ? '#ef4444' : '#6366f1'}`
                      }}>
                        <Info size={14} style={{ verticalAlign: 'middle', marginRight: 6, color: '#6366f1' }} />
                        {fc.explanation}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* ─ Loan Product Suggestions ──── */}
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Target size={18} color="#6366f1" />
              Recommended Loan Products
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
              {result.loan_suggestions.map((prod, i) => (
                <div key={i} style={{
                  background: 'var(--surface)', borderRadius: 16,
                  border: '1px solid var(--border-subtle)',
                  overflow: 'hidden',
                  transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  {/* Header stripe */}
                  <div style={{
                    padding: '14px 18px',
                    background: PRODUCT_TYPE_COLORS[prod.product_type] || 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'white', marginBottom: 2 }}>{prod.product_name}</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'white' }}>{prod.suggested_amount_label}</div>
                  </div>
                  <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                      {[
                        { label: 'Tenure', value: `${prod.suggested_tenure_months}M` },
                        { label: 'Rate', value: `${prod.suggested_rate}%` },
                        { label: 'Est. EMI', value: fmtEMI(prod.emi_estimate) },
                      ].map(item => (
                        <div key={item.label} style={{
                          padding: '8px', borderRadius: 8, textAlign: 'center',
                          background: 'var(--surface-raised)'
                        }}>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{item.label}</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{item.value}</div>
                        </div>
                      ))}
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      {prod.rationale}
                    </p>
                    {i === 0 && (
                      <div style={{
                        padding: '6px 12px', borderRadius: 6, textAlign: 'center',
                        background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)',
                        fontSize: 12, fontWeight: 700, color: '#a5b4fc'
                      }}>
                        ⭐ Top Recommended Product
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ─ Strengths & Improvements ──── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Strengths */}
            <div style={{
              background: 'var(--surface)', borderRadius: 16,
              border: '1px solid rgba(16,185,129,0.2)',
              padding: 22
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <Award size={18} color="#10b981" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Key Strengths ({result.strengths.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {result.strengths.length === 0
                  ? <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>No major strengths identified yet. Work on the improvement areas below.</p>
                  : result.strengths.map((s, i) => (
                    <div key={i} style={{
                      padding: '10px 14px', borderRadius: 8,
                      background: 'rgba(16,185,129,0.06)',
                      border: '1px solid rgba(16,185,129,0.15)',
                      fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5
                    }}>{s}</div>
                  ))
                }
              </div>
            </div>

            {/* Areas of Improvement */}
            <div style={{
              background: 'var(--surface)', borderRadius: 16,
              border: '1px solid rgba(239,68,68,0.2)',
              padding: 22
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <TrendingUp size={18} color="#f59e0b" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Areas to Improve ({result.areas_of_improvement.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {result.areas_of_improvement.length === 0
                  ? <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>No major improvement areas — excellent profile!</p>
                  : result.areas_of_improvement.map((item, i) => (
                    <div key={i} style={{
                      padding: '10px 14px', borderRadius: 8,
                      background: 'rgba(245,158,11,0.06)',
                      border: '1px solid rgba(245,158,11,0.15)',
                      fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5,
                      display: 'flex', gap: 8, alignItems: 'flex-start'
                    }}>
                      <ArrowRight size={14} color="#f59e0b" style={{ marginTop: 3, flexShrink: 0 }} />
                      <span>{item}</span>
                    </div>
                  ))
                }
              </div>
            </div>
          </div>

          {/* ─ Data Quality Footer ──── */}
          <div style={{
            background: 'var(--surface)', borderRadius: 12,
            border: '1px solid var(--border-subtle)', padding: '14px 20px',
            display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap'
          }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Info size={14} />
              <strong>Data Completeness:</strong>
              <span style={{ color: result.data_completeness_pct >= 70 ? '#10b981' : '#f59e0b' }}>
                {result.data_completeness_pct.toFixed(0)}%
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              <strong>Sources:</strong> {result.data_sources_used.join(' · ')}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              Generated: {new Date(result.as_of_date).toLocaleString('en-IN')}
            </div>
          </div>

        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
