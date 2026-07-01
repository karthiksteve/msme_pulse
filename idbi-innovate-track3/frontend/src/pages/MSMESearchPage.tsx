/**
 * MSME Directory / Search Page
 * Filterable, paginated table of all MSMEs with quick-view links.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { fetchMSMEs } from '../api/client'
import type { MSME, MSMEStatus } from '../types'

const STATUS_BADGE: Record<MSMEStatus, string> = {
  active: 'badge-success',
  inactive: 'badge-muted',
  npa: 'badge-danger',
  closed: 'badge-warning',
}

export function MSMESearchPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [state, setState] = useState('')
  const [status, setStatus] = useState<MSMEStatus | ''>('')

  const { data, isLoading } = useQuery({
    queryKey: ['msmes', page, search, state, status],
    queryFn: () => fetchMSMEs({
      page,
      page_size: 20,
      ...(search ? { legal_name: search } : {}),
      ...(state ? { state } : {}),
      ...(status ? { status } : {}),
    }),
    staleTime: 15_000,
  })

  const msmes: MSME[] = data?.msmes ?? []
  const total: number = data?.total ?? 0
  const totalPages = Math.ceil(total / 20)

  const STATES = [
    'Maharashtra', 'Tamil Nadu', 'Karnataka', 'Gujarat', 'Haryana',
    'Delhi', 'Kerala', 'Telangana', 'Uttar Pradesh', 'West Bengal',
  ]

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">MSME Directory</h1>
          <p className="page-subtitle">{total.toLocaleString('en-IN')} MSMEs indexed · Search, filter, and analyse</p>
        </div>
      </div>

      {/* ── Search & Filters ────────────────────────────────────────── */}
      <div className="card mb-lg">
        <div className="card-body">
          <div className="flex gap-md items-center" style={{ flexWrap: 'wrap' }}>
            <div className="search-bar" style={{ flex: '1 1 280px' }}>
              <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <input
                placeholder="Search by business name…"
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1) }}
              />
            </div>

            <select
              className="input"
              style={{ flex: '0 0 180px' }}
              value={state}
              onChange={e => { setState(e.target.value); setPage(1) }}
            >
              <option value="">All States</option>
              {STATES.map(s => <option key={s}>{s}</option>)}
            </select>

            <select
              className="input"
              style={{ flex: '0 0 150px' }}
              value={status}
              onChange={e => { setStatus(e.target.value as MSMEStatus | ''); setPage(1) }}
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="npa">NPA</option>
              <option value="closed">Closed</option>
            </select>

            {(search || state || status) && (
              <button className="btn btn-ghost btn-sm" onClick={() => {
                setSearch(''); setState(''); setStatus(''); setPage(1)
              }}>
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Table ───────────────────────────────────────────────────── */}
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Business Name</th>
                <th>GSTIN</th>
                <th>City / State</th>
                <th>Constitution</th>
                <th>NIC Code</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j}>
                        <div className="skeleton" style={{ height: 14, width: '70%' }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : msmes.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <Search size={32} />
                      <p>No MSMEs found matching your criteria.<br />Try adjusting the filters.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                msmes.map(m => (
                  <tr key={m.id} onClick={() => navigate(`/msme/${m.id}`)}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{m.legal_name}</div>
                      {m.trade_name && m.trade_name !== m.legal_name && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.trade_name}</div>
                      )}
                    </td>
                    <td>
                      <span className="font-mono" style={{ fontSize: 12 }}>{m.gstin}</span>
                    </td>
                    <td>
                      <div>{m.city ?? '—'}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.state}</div>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{m.constitution ?? '—'}</td>
                    <td>
                      <span className="badge badge-muted">{m.nic_code ?? '—'}</span>
                    </td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[m.status]}`}>{m.status}</span>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => navigate(`/msme/${m.id}`)}
                      >
                        <ExternalLink size={13} /> View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Page {page} of {totalPages} · {total.toLocaleString('en-IN')} MSMEs
            </span>
            <div className="flex gap-sm">
              <button
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
