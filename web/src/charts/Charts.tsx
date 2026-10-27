import { useMemo, type ReactNode } from 'react'
import { SENTIMENTS, type Sentiment } from '../lib/api'
import { pct, SENTIMENT_FILL } from '../lib/format'
import { useGrow } from '../lib/motion'

export interface StackRow {
  key: string
  label: ReactNode
  sub?: string
  positive: number
  neutral: number
  negative: number
  value?: string
  onClick?: () => void
}

/** Horizontal stacked bars. mode "share" fills each row to 100%; mode "count" scales to the largest row. */
export function StackBars({ rows, mode = 'share', testid }: { rows: StackRow[]; mode?: 'share' | 'count'; testid?: string }) {
  const max = useMemo(() => Math.max(1, ...rows.map((r) => r.positive + r.neutral + r.negative)), [rows])
  const ref = useGrow<HTMLDivElement>([rows, mode])
  return (
    <div className="hbars" ref={ref} data-testid={testid}>
      {rows.map((r) => {
        const total = r.positive + r.neutral + r.negative
        const denom = mode === 'share' ? Math.max(total, 1) : max
        const title = SENTIMENTS.map((s) => `${s}: ${r[s]}`).join(', ')
        return (
          <div
            key={r.key}
            className={`hbar ${r.onClick ? 'clickable' : ''}`}
            onClick={r.onClick}
            role={r.onClick ? 'button' : undefined}
            tabIndex={r.onClick ? 0 : undefined}
            onKeyDown={(e) => r.onClick && (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), r.onClick())}
            title={title}
            data-row={r.key}
          >
            <div className="hbar-label">
              {r.label}
              {r.sub && <small>{r.sub}</small>}
            </div>
            <div className="hbar-track" style={mode === 'count' ? { background: 'transparent' } : undefined}>
              <div data-grow="x" style={{ display: 'flex', width: mode === 'share' ? '100%' : `${(100 * total) / denom}%` }}>
                {SENTIMENTS.map((s) =>
                  r[s] > 0 ? <span key={s} style={{ width: `${(100 * r[s]) / Math.max(total, 1)}%`, background: SENTIMENT_FILL[s] }} data-s={s} data-n={r[s]} /> : null,
                )}
              </div>
            </div>
            <div className="hbar-value">{r.value ?? (mode === 'share' ? `${r.negative}/${total} neg` : total)}</div>
          </div>
        )
      })}
    </div>
  )
}

/** Plain horizontal bars (one value per row). */
export function ValueBars({ rows, color = 'var(--sage)', max, format = (v: number) => String(v) }: {
  rows: { key: string; label: ReactNode; value: number; onClick?: () => void }[]
  color?: string
  max?: number
  format?: (v: number) => string
}) {
  const m = max ?? Math.max(1e-9, ...rows.map((r) => r.value))
  const ref = useGrow<HTMLDivElement>([rows])
  return (
    <div className="hbars" ref={ref}>
      {rows.map((r) => (
        <div key={r.key} className={`hbar ${r.onClick ? 'clickable' : ''}`} onClick={r.onClick} data-row={r.key}>
          <div className="hbar-label">{r.label}</div>
          <div className="hbar-track" style={{ background: 'transparent' }}>
            <span data-grow="x" style={{ width: `${(100 * r.value) / m}%`, background: color }} />
          </div>
          <div className="hbar-value">{format(r.value)}</div>
        </div>
      ))}
    </div>
  )
}

export function SentimentStrip({ counts }: { counts: Record<Sentiment, number> }) {
  const total = Math.max(1, SENTIMENTS.reduce((a, s) => a + (counts[s] || 0), 0))
  const ref = useGrow<HTMLDivElement>([counts])
  return (
    <div ref={ref}>
      <div className="strip" data-grow="x" data-testid="sentiment-strip">
        {SENTIMENTS.map((s) =>
          counts[s] > 0 ? (
            <div key={s} style={{ width: `${(100 * counts[s]) / total}%`, background: SENTIMENT_FILL[s] }} title={`${s}: ${counts[s]} reviews`}>
              {counts[s] / total >= 0.07 ? pct(counts[s] / total) : ''}
            </div>
          ) : null,
        )}
      </div>
    </div>
  )
}

export function TrendBars({ data }: { data: { period: string; positive: number; neutral: number; negative: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.positive + d.neutral + d.negative))
  const ref = useGrow<HTMLDivElement>([data])
  if (!data.length) return null
  return (
    <div ref={ref}>
      <div className="vbars" data-testid="trend">
        {data.map((d) => {
          const t = d.positive + d.neutral + d.negative
          return (
            <div key={d.period} className="vbar" title={`${d.period}: ${d.positive} positive, ${d.neutral} neutral, ${d.negative} negative`}>
              <div data-grow="y" style={{ height: `${(100 * t) / max}%`, display: 'flex', flexDirection: 'column-reverse' }}>
                {SENTIMENTS.map((s) => (d[s] ? <span key={s} style={{ height: `${(100 * d[s]) / t}%`, background: SENTIMENT_FILL[s] }} /> : null))}
              </div>
            </div>
          )
        })}
      </div>
      <div className="vbar-axis">
        <span>{data[0].period}</span>
        <span>{data[data.length - 1].period}</span>
      </div>
    </div>
  )
}

export function ProbabilityBars({ p }: { p: { positive: number | null; neutral: number | null; negative: number | null } }) {
  return (
    <ValueBars
      max={1}
      format={(v) => pct(v)}
      rows={SENTIMENTS.map((s) => ({ key: s, label: s.charAt(0).toUpperCase() + s.slice(1), value: p[s] ?? 0 }))}
      color="var(--brand)"
    />
  )
}

export function IndicatorScale({ value }: { value: number | null }) {
  const v = value ?? 0
  return (
    <div className="scale" aria-label={`Indicator ${v.toFixed(1)} out of 100`} data-testid="indicator-scale">
      <div className="band" style={{ left: 0, width: '40%', background: 'var(--neg-fill)' }} />
      <div className="band" style={{ left: '40%', width: '20%', background: 'var(--neu-fill)' }} />
      <div className="band" style={{ left: '60%', width: '40%', background: 'var(--pos-fill)' }} />
      <div className="marker" style={{ left: `calc(${v}% - 1px)` }} />
      <div className="mono" style={{ position: 'absolute', top: 0, left: `clamp(0px, calc(${v}% - 20px), calc(100% - 44px))`, color: 'var(--brand)', fontSize: 13 }}>
        {value === null ? 'n/a' : v.toFixed(1)}
      </div>
      <div className="ticks">
        {[0, 20, 40, 60, 80, 100].map((t) => <span key={t}>{t}</span>)}
      </div>
    </div>
  )
}

export function GroupedBars({ groups, series }: {
  groups: { key: string; label: ReactNode; values: number[] }[]
  series: { name: string; color: string }[]
}) {
  const ref = useGrow<HTMLDivElement>([groups])
  return (
    <div ref={ref}>
      <div className="legend">
        {series.map((s) => (
          <span key={s.name} className="chip" style={{ color: 'var(--muted)' }}>
            <i style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
      <div className="grouped" style={{ ['--cols' as any]: groups.length, marginTop: 28 }}>
        {groups.map((g) => (
          <div key={g.key} className="g">
            {g.values.map((v, i) => (
              <span key={i} data-grow="y" style={{ height: `${Math.max(0, Math.min(1, v)) * 100}%`, background: series[i].color }} title={`${series[i].name}: ${v.toFixed(3)}`}>
                <b>{v.toFixed(2)}</b>
              </span>
            ))}
          </div>
        ))}
      </div>
      <div className="grouped-labels" style={{ ['--cols' as any]: groups.length }}>
        {groups.map((g) => <div key={g.key}>{g.label}</div>)}
      </div>
    </div>
  )
}

export function ReliabilityChart({ bins }: { bins: { confidence: number; accuracy: number; count: number }[] }) {
  const W = 420, H = 300, P = 36
  const x = (v: number) => P + v * (W - P - 10)
  const y = (v: number) => H - P - v * (H - P - 10)
  const path = bins.map((b, i) => `${i ? 'L' : 'M'}${x(b.confidence).toFixed(1)},${y(b.accuracy).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Calibration: predicted confidence against observed accuracy">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t} className="grid">
          <line x1={x(0)} x2={x(1)} y1={y(t)} y2={y(t)} />
          <text x={P - 8} y={y(t) + 4} textAnchor="end">{t}</text>
          <text x={x(t)} y={H - P + 18} textAnchor="middle">{t}</text>
        </g>
      ))}
      <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="var(--muted)" strokeDasharray="3 4" />
      <path d={path} fill="none" stroke="var(--brand)" strokeWidth={2} />
      {bins.map((b) => (
        <rect key={b.confidence} x={x(b.confidence) - 4 - Math.min(b.count, 60) / 12} y={y(b.accuracy) - 4 - Math.min(b.count, 60) / 12}
          width={8 + Math.min(b.count, 60) / 6} height={8 + Math.min(b.count, 60) / 6} fill="var(--brand)">
          <title>{`mean confidence ${b.confidence.toFixed(2)}, accuracy ${b.accuracy.toFixed(2)}, ${b.count} reviews`}</title>
        </rect>
      ))}
      <text x={W / 2} y={H - 4} textAnchor="middle">predicted top-class probability</text>
    </svg>
  )
}
