// Typed client for the Sentiq FastAPI backend (api/main.py).
import type { Filters } from './store'

export type Sentiment = 'positive' | 'neutral' | 'negative'
export const SENTIMENTS: Sentiment[] = ['positive', 'neutral', 'negative']

export interface ValidationReport {
  total_records: number
  valid_records: number
  excluded_records: number
  exclusion_reasons: Record<string, number>
  truncated_reviews: number
  unparseable_dates: number
  unparseable_ratings: number
  missing_metadata: Record<string, number>
  mapped_columns: Record<string, string | null>
  warnings: string[]
}
export interface DatasetSummary {
  id: string
  name: string
  kind: 'demo' | 'upload'
  report: ValidationReport
  valid_reviews: number
  options: { course: string[]; instructor: string[]; semester: string[]; aspect: string[]; date_min: string | null; date_max: string | null }
}
export interface AspectRow {
  aspect_id: string
  aspect: string
  reviews: number
  coverage: number
  positive: number
  neutral: number
  negative: number
  uncertain: number
  positive_share: number
  negative_share: number
  aspect_score: number | null
  enough_evidence: boolean
}
export interface KeywordRow { term: string; reviews: number; positive: number; neutral: number; negative: number; share_of_reviews: number; net_sentiment: number }
export interface PhraseRow { phrase: string; reviews: number; positive: number; neutral: number; negative: number }
export interface Topic { topic_id: number; label: string; terms: string[]; weights: number[]; n_reviews: number; positive: number; neutral: number; negative: number }
export interface Review {
  record_id: number
  review_text: string
  course: string | null
  instructor: string | null
  semester: string | null
  date: string | null
  rating: number | null
  sentiment: Sentiment | 'unavailable'
  prob_positive: number | null
  prob_neutral: number | null
  prob_negative: number | null
  confidence: number | null
  margin: number | null
  review_needed: boolean
  sentiment_score: number | null
  aspects: string
  aspect_count: number
  evidence_terms: string
  processed_text: string
  highlight_terms?: string[]
}
export interface Mention {
  record_id: number
  aspect_id: string
  aspect: string
  evidence: string
  sentence: string
  terms: string
  match_type: string
  negated: boolean
  aspect_sentiment: Sentiment
  aspect_prob_positive: number
  aspect_prob_neutral: number
  aspect_prob_negative: number
  aspect_confidence: number
  aspect_review_needed: boolean
  review_text?: string
}
export interface Insight { kind: string; tone: string; text: string }
export interface Kpis {
  valid_reviews: number
  excluded_records: number
  counts: Record<Sentiment, number>
  shares: Record<Sentiment, number>
  avg_sentiment_score: number | null
  effectiveness: number | null
  review_needed: number
  with_aspect: number
  avg_words: number
}
export interface Overview {
  selection: string
  dataset: { id: string; name: string; kind: string }
  kpis: Kpis
  total_records: number
  exclusion_reasons: Record<string, number>
  most_positive: AspectRow | null
  most_negative: AspectRow | null
  aspects: AspectRow[]
  insights: Insight[]
  keywords: KeywordRow[]
  topics: { ok: boolean; message: string; items: Topic[] }
  trend: { period: string; positive: number; neutral: number; negative: number }[]
  points: { id: number; score: number; confidence: number; sentiment: Sentiment; aspect: string | null }[]
}
export interface Recommendation {
  kind: 'issue' | 'strength'
  aspect_id: string
  aspect: string
  priority: 'high' | 'medium' | 'keep'
  headline: string
  supporting_reviews: number
  aspect_reviews: number
  share: number
  action: string
  examples: { record_id: number; evidence: string; review: string; probability: number }[]
  caveats: string[]
}
export interface Meta {
  product: string
  descriptor: string
  tagline: string
  academic_title: string
  model: { available: boolean; source: string; message: string; trained_at: string | null }
  limits: Record<string, number>
  aspects: { id: string; label: string; description: string; terms: string[]; phrases: string[]; context_terms: string[] }[]
  roles: { role: string; label: string; required: boolean }[]
  training_dataset: Record<string, unknown> | null
  versions: Record<string, string | null>
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function filterParams(f: Filters, extra: Record<string, string | number | boolean | undefined> = {}): string {
  const p = new URLSearchParams()
  for (const key of ['course', 'instructor', 'semester', 'sentiment', 'aspect'] as const) {
    for (const v of f[key]) p.append(key, v)
  }
  if (f.confidence !== 'all') p.set('confidence', f.confidence)
  if (f.dateFrom) p.set('date_from', f.dateFrom)
  if (f.dateTo) p.set('date_to', f.dateTo)
  for (const [k, v] of Object.entries(extra)) if (v !== undefined && v !== '') p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the Sentiq server. Check that it is running.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const api = {
  meta: () => request<Meta>('/api/meta'),
  model: () => request<any>('/api/model'),
  dataset: (id: string) => request<DatasetSummary>(`/api/datasets/${id}`),
  overview: (id: string, f: Filters) => request<Overview>(`/api/datasets/${id}/overview${filterParams(f)}`),
  reviews: (id: string, f: Filters, q: string, sort: string, offset: number, limit: number) =>
    request<{ total: number; selection: string; items: Review[] }>(`/api/datasets/${id}/reviews${filterParams(f, { q, sort, offset, limit })}`),
  review: (id: string, rid: number) => request<{ review: Review; mentions: Mention[]; ambiguous: any[] }>(`/api/datasets/${id}/reviews/${rid}`),
  aspects: (id: string, f: Filters) =>
    request<{ selection: string; reviews: number; with_aspect: number; summary: AspectRow[]; unmatched: Review[]; ambiguous: any[] }>(
      `/api/datasets/${id}/aspects${filterParams(f)}`,
    ),
  evidence: (id: string, aspectId: string, f: Filters, clause: string[]) => {
    const qs = filterParams(f)
    const extra = clause.map((c) => `clause_sentiment=${encodeURIComponent(c)}`).join('&')
    return request<{ items: (Mention & { review_text: string; review_sentiment: string; review_confidence: number })[] }>(
      `/api/datasets/${id}/aspects/${aspectId}/evidence${qs}${extra ? (qs ? '&' : '?') + extra : ''}`,
    )
  },
  keywords: (id: string, f: Filters, n: number, minReviews: number, hide: boolean, top: number) =>
    request<{ selection: string; total_terms: number; terms: KeywordRow[]; all_terms: string[]; noun_phrases: PhraseRow[] }>(
      `/api/datasets/${id}/keywords${filterParams(f, { n, min_reviews: minReviews, hide_generic: hide, top })}`,
    ),
  keywordReviews: (id: string, f: Filters, term: string, n: number) =>
    request<{ total: number; items: Review[] }>(`/api/datasets/${id}/keywords/reviews${filterParams(f, { term, n })}`),
  topics: (id: string, f: Filters, k: number) =>
    request<{ ok: boolean; message: string; unassigned: number | null; items: (Topic & { representatives: Review[] })[] }>(
      `/api/datasets/${id}/topics${filterParams(f, { k })}`,
    ),
  effectiveness: (id: string, f: Filters, groupBy: string) =>
    request<{
      selection: string
      reviews: number
      counts: Record<Sentiment, number>
      indicator: number | null
      small_sample: boolean
      aspects: AspectRow[]
      groups: { group: string; reviews: number; positive: number; neutral: number; negative: number; indicator: number | null; evidence: string }[]
      group_options: string[]
      recommendations: Recommendation[]
    }>(`/api/datasets/${id}/effectiveness${filterParams(f, { group_by: groupBy })}`),
  validation: (id: string) => request<{ report: ValidationReport; excluded: any[] }>(`/api/datasets/${id}/validation`),
  analyzeText: (text: string) =>
    request<{ prediction: Review & { margin: number }; aspects: any[]; ambiguous: any[]; processed_text: string }>('/api/analyze-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<{
      upload_id: string
      filename: string
      rows: number
      columns: string[]
      encoding: string
      delimiter: string
      truncated: boolean
      original_rows: number
      preview: Record<string, unknown>[]
      suggested_mapping: Record<string, string | null>
    }>('/api/uploads', { method: 'POST', body })
  },
  analyzeUpload: (uploadId: string, mapping: Record<string, string | null>, name: string) =>
    request<DatasetSummary>(`/api/uploads/${uploadId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mapping, name }),
    }),
  exportUrl: (id: string, kind: string, f: Filters, q = '') => `/api/datasets/${id}/export/${kind}${filterParams(f, { q: q.trim() || undefined })}`,
}
