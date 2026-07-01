// API client — centralised axios instance pointing at FastAPI backend
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── MSME endpoints ──────────────────────────────────────────────────
export const fetchPortfolioSummary = () =>
  api.get('/api/v1/dashboard/portfolio/summary').then(r => r.data)

export const fetchNeedDistribution = (days = 90) =>
  api.get(`/api/v1/dashboard/portfolio/need-distribution?days=${days}`).then(r => r.data)

export const fetchProductStats = () =>
  api.get('/api/v1/dashboard/portfolio/product-stats').then(r => r.data)

export const fetchConversionFunnel = () =>
  api.get('/api/v1/products/recommendations/analytics/conversion-funnel').then(r => r.data)

export const fetchPortfolioHeatmap = (state?: string) =>
  api.get('/api/v1/dashboard/portfolio/heatmap' + (state ? `?state=${state}` : '')).then(r => r.data)

export const fetchMSMEs = (params: Record<string, string | number | boolean | undefined>) =>
  api.get('/api/v1/msmes/', { params }).then(r => r.data)

export const fetchMSMEById = (id: string) =>
  api.get(`/api/v1/dashboard/msme/${id}/full`).then(r => r.data)

export const fetchGSTReturns = (msmeId: string, limit = 12) =>
  api.get(`/api/v1/gst/gst-returns/msme/${msmeId}?limit=${limit}`).then(r => r.data)

export const updateRecommendationStatus = (id: string, status: string) =>
  api.patch(`/api/v1/products/recommendations/${id}/status?status=${status}`).then(r => r.data)
