// App-wide state: active dataset, global filters and theme. Filters persist in the URL so views can be shared.
import { create } from 'zustand'

export interface Filters {
  course: string[]
  instructor: string[]
  semester: string[]
  sentiment: string[]
  aspect: string[]
  confidence: 'all' | 'confident' | 'review'
  dateFrom: string | null
  dateTo: string | null
}

export const EMPTY_FILTERS: Filters = {
  course: [],
  instructor: [],
  semester: [],
  sentiment: [],
  aspect: [],
  confidence: 'all',
  dateFrom: null,
  dateTo: null,
}

export function activeFilterCount(f: Filters): number {
  return (
    f.course.length + f.instructor.length + f.semester.length + f.sentiment.length + f.aspect.length +
    (f.confidence !== 'all' ? 1 : 0) + (f.dateFrom ? 1 : 0) + (f.dateTo ? 1 : 0)
  )
}

function readUrl(): { filters: Filters; dataset: string | null } {
  const p = new URLSearchParams(window.location.search)
  const list = (k: string) => p.getAll(k)
  const conf = p.get('confidence')
  return {
    dataset: p.get('dataset'),
    filters: {
      course: list('course'),
      instructor: list('instructor'),
      semester: list('semester'),
      sentiment: list('sentiment'),
      aspect: list('aspect'),
      confidence: conf === 'confident' || conf === 'review' ? conf : 'all',
      dateFrom: p.get('date_from'),
      dateTo: p.get('date_to'),
    },
  }
}

export function writeUrl(datasetId: string, f: Filters) {
  const p = new URLSearchParams()
  if (datasetId !== 'demo') p.set('dataset', datasetId)
  for (const key of ['course', 'instructor', 'semester', 'sentiment', 'aspect'] as const) for (const v of f[key]) p.append(key, v)
  if (f.confidence !== 'all') p.set('confidence', f.confidence)
  if (f.dateFrom) p.set('date_from', f.dateFrom)
  if (f.dateTo) p.set('date_to', f.dateTo)
  const qs = p.toString()
  const url = window.location.pathname + (qs ? `?${qs}` : '') + window.location.hash
  window.history.replaceState(window.history.state, '', url)
}

type Theme = 'light' | 'dark'

function readTheme(): Theme {
  try {
    const t = localStorage.getItem('sentiq-theme')
    if (t === 'dark' || t === 'light') return t
  } catch {
    /* storage may be blocked */
  }
  return 'light'
}

interface State {
  datasetId: string
  filters: Filters
  theme: Theme
  filterPanel: boolean
  setDataset: (id: string) => void
  setFilters: (patch: Partial<Filters>) => void
  toggle: (key: 'course' | 'instructor' | 'semester' | 'sentiment' | 'aspect', value: string) => void
  clearFilters: () => void
  setTheme: (t: Theme) => void
  openPanel: (open: boolean) => void
}

const initial = readUrl()

export const useApp = create<State>((set, get) => ({
  datasetId: initial.dataset || 'demo',
  filters: initial.filters,
  theme: readTheme(),
  filterPanel: false,
  setDataset: (id) => {
    set({ datasetId: id, filters: { ...EMPTY_FILTERS } })
    writeUrl(id, EMPTY_FILTERS)
  },
  setFilters: (patch) => {
    const filters = { ...get().filters, ...patch }
    set({ filters })
    writeUrl(get().datasetId, filters)
  },
  toggle: (key, value) => {
    const cur = get().filters[key]
    const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value]
    get().setFilters({ [key]: next } as Partial<Filters>)
  },
  clearFilters: () => {
    set({ filters: { ...EMPTY_FILTERS } })
    writeUrl(get().datasetId, EMPTY_FILTERS)
  },
  setTheme: (t) => {
    set({ theme: t })
    document.documentElement.dataset.theme = t
    try {
      localStorage.setItem('sentiq-theme', t)
    } catch {
      /* ignore */
    }
  },
  openPanel: (open) => set({ filterPanel: open }),
}))
