// Shared TypeScript types matching the backend Pydantic schemas

export type MSMEStatus = 'active' | 'inactive' | 'npa' | 'closed'
export type NeedCategory =
  | 'working_capital'
  | 'machinery_capex'
  | 'business_expansion'
  | 'inventory_funding'
  | 'trade_finance'
  | 'digital_transformation'

export type ProductType =
  | 'cc_od'
  | 'machinery_term_loan'
  | 'business_expansion_loan'
  | 'inventory_funding'
  | 'trade_finance'
  | 'digital_business_loan'

export type RecStatus = 'generated' | 'sent' | 'viewed' | 'applied' | 'approved' | 'rejected'

export interface MSME {
  id: string
  gstin: string
  pan: string
  cin?: string
  legal_name: string
  trade_name?: string
  city?: string
  state?: string
  pincode?: string
  nic_code?: string
  nic_description?: string
  incorporation_date?: string
  constitution?: string
  status: MSMEStatus
  gst_registration_date?: string
  created_at: string
  updated_at: string
}

export interface GSTReturn {
  id: string
  msme_id: string
  return_type: string
  financial_year: string
  tax_period: string
  total_revenue: number
  b2b_revenue: number
  b2c_revenue: number
  export_revenue: number
  gst_liability: number
  itc_available: number
  itc_claimed: number
  tax_paid: number
  filing_status: string
  filing_date?: string
}

export interface AAAccount {
  id: string
  msme_id: string
  fi_name: string
  account_type: string
  sanctioned_limit: number
  outstanding_amount: number
  drawing_power: number
  interest_rate: number
  repayment_status: string
  days_past_due: number
  overdue_amount: number
}

export interface NeedPrediction {
  id: string
  msme_id: string
  need_categories: Record<NeedCategory, number>
  top_need: NeedCategory
  confidence_score: number
  shap_values: Record<string, number>
  key_drivers: string[]
  model_version: string
  prediction_date: string
}

export interface ProductRecommendation {
  id: string
  msme_id: string
  need_prediction_id?: string
  product_type: ProductType
  eligibility_score: number
  ranking_score: number
  rank: number
  suggested_amount: number
  suggested_tenure_months: number
  suggested_rate: number
  eligibility_rules_passed: string[]
  eligibility_rules_failed: string[]
  shap_explanation: Record<string, number>
  business_rationale?: string
  status: RecStatus
  created_at: string
}

export interface PortfolioSummary {
  total_msmes: number
  active_msmes: number
  msmes_with_gst: number
  msmes_with_aa: number
  need_predictions_generated: number
  product_recommendations: number
  approved_recommendations: number
  conversion_rate: number
}

export interface NeedDistribution {
  category: NeedCategory
  count: number
  percentage: number
  avg_confidence: number
}

export interface ProductMatchStats {
  product_type: ProductType
  recommendations: number
  avg_eligibility: number
  avg_ranking_score: number
  estimated_disbursement_cr: number
}

export interface FullMSMEProfile {
  msme: MSME
  gst_returns: GSTReturn[]
  aa_accounts: AAAccount[]
  latest_need_prediction: NeedPrediction | null
  product_recommendations: ProductRecommendation[]
}
