import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api, ApiError, SENTIMENTS } from '../lib/api'
import { scrollToTop } from '../lib/motion'
import { activeFilterCount, useApp } from '../lib/store'
import { Segmented } from './ui'

const NAV = [
  { to: '/', label: 'Overview' },
  { to: '/data', label: 'Data' },
  { to: '/explore', label: 'Explore' },
  { to: '/aspects', label: 'Aspects' },
  { to: '/topics', label: 'Topics' },
  { to: '/insights', label: 'Insights' },
  { to: '/model', label: 'Model' },
  { to: '/method', label: 'Method' },
]

export function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <rect x="4" y="4" width="40" height="40" fill="#702F45" />
      <rect x="12" y="15" width="24" height="3" fill="#F5F0E8" />
      <rect x="12" y="22.5" width="17" height="3" fill="#F5F0E8" />
      <rect x="12" y="30" width="10" height="3" fill="#8AAB91" />
    </svg>
  )
}

function Header() {
  const { theme, setTheme } = useApp()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  useEffect(() => setOpen(false), [loc.pathname])
  return (
    <header className="header">
      <div className="wrap">
        <NavLink to={{ pathname: '/', search: window.location.search }} className="brand" aria-label="Sentiq home">
          <Mark />
          Sentiq
        </NavLink>
        <nav className={`nav ${open ? 'open' : ''}`} aria-label="Main">
          {NAV.map((n) => (
            <NavLink key={n.to} to={{ pathname: n.to, search: window.location.search }} end={n.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="header-tools">
          <Segmented
            label="Colour theme"
            value={theme}
            options={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
            ]}
            onChange={setTheme}
          />
          <button type="button" className="btn ghost menu-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? 'Close' : 'Menu'}
          </button>
        </div>
      </div>
    </header>
  )
}

function SelectionBar() {
  const { datasetId, filters, setFilters, toggle, clearFilters, openPanel, setDataset } = useApp()
  const ds = useQuery({ queryKey: ['dataset', datasetId], queryFn: () => api.dataset(datasetId), retry: false })
  useEffect(() => {
    if (ds.error instanceof ApiError && ds.error.status === 404 && datasetId !== 'demo') setDataset('demo')
  }, [ds.error, datasetId, setDataset])
  const tokens: { key: string; label: string; remove: () => void }[] = []
  for (const key of ['course', 'instructor', 'semester', 'sentiment', 'aspect'] as const)
    for (const v of filters[key]) tokens.push({ key: key + v, label: v, remove: () => toggle(key, v) })
  if (filters.confidence !== 'all')
    tokens.push({ key: 'conf', label: filters.confidence === 'confident' ? 'Confident only' : 'Review needed only', remove: () => setFilters({ confidence: 'all' }) })
  if (filters.dateFrom) tokens.push({ key: 'df', label: `from ${filters.dateFrom}`, remove: () => setFilters({ dateFrom: null }) })
  if (filters.dateTo) tokens.push({ key: 'dt', label: `to ${filters.dateTo}`, remove: () => setFilters({ dateTo: null }) })
  const isDemo = ds.data?.kind === 'demo'
  return (
    <div className="selbar">
      <div className="wrap">
        <span>
          <span className="dot" style={{ background: isDemo ? 'var(--neu)' : 'var(--sage)' }} />
          <span className="label" style={{ marginRight: 8 }}>{isDemo ? 'Synthetic demo data' : 'Uploaded data'}</span>
          <strong data-testid="dataset-name">{ds.data?.name ?? '...'}</strong>
          {ds.data && <span className="muted"> · {ds.data.report.valid_records} valid, {ds.data.report.excluded_records} excluded</span>}
        </span>
        <span style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 6 }}>
          {tokens.map((t) => (
            <span className="token" key={t.key}>
              {t.label}
              <button type="button" aria-label={`Remove filter ${t.label}`} onClick={t.remove}>×</button>
            </span>
          ))}
        </span>
        <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 14, alignItems: 'center' }}>
          {tokens.length > 0 && (
            <button type="button" className="link-btn" onClick={clearFilters}>
              Clear filters
            </button>
          )}
          <button type="button" className="btn ghost" style={{ padding: '6px 14px' }} onClick={() => openPanel(true)} data-testid="open-filters">
            Filters{activeFilterCount(filters) ? ` (${activeFilterCount(filters)})` : ''}
          </button>
        </span>
      </div>
    </div>
  )
}

function ToggleList({ k, options }: { k: 'course' | 'instructor' | 'semester' | 'sentiment' | 'aspect'; options: string[] }) {
  const { filters, toggle } = useApp()
  return (
    <div className="checklist">
      {options.map((o) => (
        <button type="button" key={o} className="check" aria-pressed={filters[k].includes(o)} onClick={() => toggle(k, o)}>
          {o}
        </button>
      ))}
    </div>
  )
}

function FilterPanel() {
  const { datasetId, filters, setFilters, clearFilters, filterPanel, openPanel } = useApp()
  const ds = useQuery({ queryKey: ['dataset', datasetId], queryFn: () => api.dataset(datasetId), retry: false })
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && openPanel(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [openPanel])
  if (!filterPanel) return null
  const o = ds.data?.options
  return (
    <>
      <div className="panel-backdrop" onClick={() => openPanel(false)} />
      <aside className="panel" role="dialog" aria-modal="true" aria-label="Filters" data-lenis-prevent>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h3>Filters</h3>
          <button type="button" className="link-btn" onClick={() => openPanel(false)}>Done</button>
        </div>
        <p className="muted small" style={{ marginTop: 8 }}>Every page, chart, recommendation and export uses this selection.</p>
        {o && (
          <>
            {o.course.length > 0 && (
              <div className="group"><div className="label" style={{ marginBottom: 10 }}>Course</div><ToggleList k="course" options={o.course} /></div>
            )}
            {o.instructor.length > 0 && (
              <div className="group"><div className="label" style={{ marginBottom: 10 }}>Instructor</div><ToggleList k="instructor" options={o.instructor} /></div>
            )}
            {o.semester.length > 0 && (
              <div className="group"><div className="label" style={{ marginBottom: 10 }}>Semester</div><ToggleList k="semester" options={o.semester} /></div>
            )}
            <div className="group"><div className="label" style={{ marginBottom: 10 }}>Predicted sentiment</div><ToggleList k="sentiment" options={SENTIMENTS} /></div>
            <div className="group"><div className="label" style={{ marginBottom: 10 }}>Mentions aspect</div><ToggleList k="aspect" options={o.aspect} /></div>
            <div className="group">
              <div className="label" style={{ marginBottom: 10 }}>Prediction confidence</div>
              <Segmented
                label="Prediction confidence"
                value={filters.confidence}
                options={[
                  { value: 'all', label: 'All' },
                  { value: 'confident', label: 'Confident only' },
                  { value: 'review', label: 'Review needed' },
                ]}
                onChange={(v) => setFilters({ confidence: v })}
              />
            </div>
            {o.date_min && o.date_max && (
              <div className="group">
                <div className="label" style={{ marginBottom: 10 }}>Date range</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <label className="field"><span>From</span>
                    <input className="input" type="date" min={o.date_min} max={o.date_max} value={filters.dateFrom ?? ''}
                      onChange={(e) => setFilters({ dateFrom: e.target.value || null })} data-testid="date-from" />
                  </label>
                  <label className="field"><span>To</span>
                    <input className="input" type="date" min={o.date_min} max={o.date_max} value={filters.dateTo ?? ''}
                      onChange={(e) => setFilters({ dateTo: e.target.value || null })} data-testid="date-to" />
                  </label>
                </div>
                <p className="small muted" style={{ marginTop: 8 }}>Reviews without a date are kept in every range.</p>
              </div>
            )}
            <div className="group" style={{ display: 'flex', gap: 12 }}>
              <button type="button" className="btn" onClick={() => openPanel(false)}>Show results</button>
              <button type="button" className="btn ghost" onClick={clearFilters}>Clear all</button>
            </div>
          </>
        )}
      </aside>
    </>
  )
}

function Footer() {
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  return (
    <footer className="footer">
      <div className="wrap">
        <div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', color: 'var(--text)' }}>
            <Mark size={22} />
            <strong style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 18 }}>Sentiq</strong>
          </div>
          <p style={{ marginTop: 10 }}>NLP-Powered Course Feedback Intelligence. Every response tells a story.</p>
        </div>
        <div>
          <p>Academic project: <i>{meta.data?.academic_title ?? 'An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit'}</i></p>
          <p style={{ marginTop: 8 }}>
            Sentiment comes from a trained Logistic Regression model and aspect analysis is rule-assisted. Indicators summarise expressed student opinion and should be read alongside other evidence about teaching.
          </p>
        </div>
      </div>
    </footer>
  )
}

export function Shell({ children }: { children: ReactNode }) {
  const loc = useLocation()
  useEffect(() => scrollToTop(), [loc.pathname])
  return (
    <>
      <a href="#main" className="link-btn" style={{ position: 'absolute', left: -9999 }}>Skip to content</a>
      <Header />
      <SelectionBar />
      <FilterPanel />
      <main id="main">{children}</main>
      <Footer />
    </>
  )
}
