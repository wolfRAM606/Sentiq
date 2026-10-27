import type { ReactNode } from 'react'
import { useCountUp } from '../lib/motion'
import { SENTIMENT_VAR } from '../lib/format'
import { ApiError } from '../lib/api'

export function SectionHead({ num, title, children }: { num: string; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="section-head">
      <div data-reveal>
        <div className="num">{num}</div>
        <h2>{title}</h2>
      </div>
      {children ? (
        <div data-reveal data-delay="0.1">
          <p>{children}</p>
        </div>
      ) : (
        <div />
      )}
    </div>
  )
}

export function Figure({ label, value, decimals = 0, prefix = '', suffix = '', note, tone }: {
  label: string
  value: number | null | undefined
  decimals?: number
  prefix?: string
  suffix?: string
  note?: ReactNode
  tone?: 'positive' | 'neutral' | 'negative' | 'brand'
}) {
  const { ref, text } = useCountUp(value, decimals)
  const color = tone === 'brand' ? 'var(--brand)' : tone ? `var(${SENTIMENT_VAR[tone]})` : undefined
  return (
    <div className="figure" data-reveal>
      <div className="label">{label}</div>
      <div className="v num-figure" style={{ color }}>
        {text !== 'n/a' && prefix}
        <span ref={ref} data-testid={`fig-${label}`}>{text}</span>
        {suffix && <span style={{ fontSize: '0.4em', color: 'var(--muted)', marginLeft: 6 }}>{suffix}</span>}
      </div>
      {note && <div className="n">{note}</div>}
    </div>
  )
}

export function Chip({ sentiment, label }: { sentiment: string; label?: string }) {
  const color = `var(${SENTIMENT_VAR[sentiment] || '--muted'})`
  return (
    <span className="chip" style={{ color }}>
      <i style={{ background: color }} />
      {label || sentiment}
    </span>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty" role="status">
      <strong>{title}</strong>
      {children}
    </div>
  )
}

export function Loading({ what = 'Loading' }: { what?: string }) {
  return (
    <div className="loading-line" role="status" aria-live="polite">
      {what}
      <div className="progress" style={{ marginTop: 10 }}>
        <i />
      </div>
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg = error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="notice error" role="alert">
      {msg}
    </div>
  )
}

export function Highlight({ text, terms }: { text: string; terms?: string[] }) {
  const list = Array.from(new Set((terms || []).filter((t) => t && t.length > 1))).sort((a, b) => b.length - a.length)
  if (!list.length) return <>{text}</>
  const esc = list.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const re = new RegExp(`\\b(${esc.join('|')})\\b`, 'gi')
  const parts = text.split(re)
  return (
    <>
      {parts.map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>))}
    </>
  )
}

export function Legend() {
  return (
    <div className="legend">
      <Chip sentiment="positive" />
      <Chip sentiment="neutral" />
      <Chip sentiment="negative" />
    </div>
  )
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}
