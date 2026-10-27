import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ProbabilityBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Highlight, Loading, SectionHead, Segmented } from '../components/ui'
import { api, type Review } from '../lib/api'
import { pct } from '../lib/format'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

const PAGE = 20

function Detail({ id }: { id: number }) {
  const { datasetId } = useApp()
  const q = useQuery({ queryKey: ['review', datasetId, id], queryFn: () => api.review(datasetId, id) })
  if (q.isLoading) return <Loading what="Loading review" />
  if (q.error) return <ErrorNote error={q.error} />
  const { review: r, mentions, ambiguous } = q.data!
  return (
    <div className="split" style={{ padding: '18px 0 8px' }} data-testid={`detail-${id}`}>
      <div>
        <div className="label" style={{ marginBottom: 10 }}>Class probabilities</div>
        <ProbabilityBars p={{ positive: r.prob_positive, neutral: r.prob_neutral, negative: r.prob_negative }} />
        <p className="small muted" style={{ marginTop: 10 }}>
          Estimates from Logistic Regression. The top value is not a calibrated certainty; see calibration on the Model page.
        </p>
        <div className="label" style={{ margin: '22px 0 8px' }}>Model input after spaCy preprocessing</div>
        <code className="mono small" style={{ display: 'block', background: 'var(--surface)', padding: 12, border: '1px solid var(--rule)' }} data-testid="processed">
          {r.processed_text || '(empty after preprocessing)'}
        </code>
        <p className="small muted" style={{ marginTop: 8 }}>Lemmas; generic stopwords removed, negators kept; words in a negation's scope carry neg_.</p>
      </div>
      <div>
        <div className="label" style={{ marginBottom: 10 }}>Aspects, with the clause that triggered each</div>
        {mentions.length ? (
          <div className="rows">
            {mentions.map((m) => (
              <div className="row" key={m.aspect_id} style={{ gridTemplateColumns: '1fr' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                    <strong>{m.aspect}</strong>
                    <Chip sentiment={m.aspect_sentiment} label={`${m.aspect_sentiment} ${pct(m.aspect_confidence)}`} />
                  </div>
                  <div className="quote" style={{ fontSize: 16, marginTop: 6 }}>"<Highlight text={m.evidence} terms={m.terms.split(',').map((t) => t.trim())} />"</div>
                  <div className="small muted" style={{ marginTop: 4 }}>
                    {m.match_type}{m.negated ? ' · negated' : ''} · matched: {m.terms}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="No aspect detected">This is reported separately from neutral sentiment.</Empty>
        )}
        {ambiguous.length > 0 && (
          <p className="small muted" style={{ marginTop: 12 }}>
            Ambiguous words without supporting context: {ambiguous.map((a: any) => `"${a.term}" (${a.aspect_label})`).join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}

function ReviewRow({ r, open, onToggle }: { r: Review; open: boolean; onToggle: () => void }) {
  return (
    <article className="review" data-testid="review" data-id={r.record_id}>
      <div className="text"><Highlight text={r.review_text} terms={r.highlight_terms} /></div>
      <div className="meta">
        <Chip sentiment={r.sentiment} />
        {r.confidence !== null && <span>confidence {pct(r.confidence)}</span>}
        {r.review_needed && r.sentiment !== 'unavailable' && <span className="warn">Review needed</span>}
        {r.aspects && r.aspects.split('; ').map((a) => <span className="tag" key={a}>{a}</span>)}
        {[r.course, r.instructor, r.semester].filter(Boolean).map((m) => <span key={m}>{m}</span>)}
        <span className="mono">#{r.record_id}</span>
        <button type="button" className="link-btn" onClick={onToggle} aria-expanded={open} data-testid={`inspect-${r.record_id}`}>
          {open ? 'Close details' : 'Inspect'}
        </button>
      </div>
      {open && <Detail id={r.record_id} />}
    </article>
  )
}

function Single() {
  const [text, setText] = useState('')
  const m = useMutation({ mutationFn: (t: string) => api.analyzeText(t) })
  const r = m.data
  return (
    <div className="split wide-right">
      <div data-reveal>
        <label className="field">
          <span>One piece of feedback</span>
          <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} data-testid="single-text"
            placeholder="The lectures were clear, but the assignment instructions were confusing." maxLength={5000} />
        </label>
        <div style={{ marginTop: 12, display: 'flex', gap: 12, alignItems: 'center' }}>
          <button type="button" className="btn" onClick={() => m.mutate(text)} disabled={m.isPending} data-testid="single-run">
            {m.isPending ? 'Analysing' : 'Analyse this text'}
          </button>
          <span className="small muted">Not added to the dataset.</span>
        </div>
        {m.error && <div style={{ marginTop: 12 }}><ErrorNote error={m.error} /></div>}
      </div>
      <div data-reveal data-delay="0.1" data-testid="single-result">
        {r ? (
          <div className="stack">
            <div>
              <div className="label">Predicted sentiment</div>
              <div className="num-figure" style={{ fontSize: 44, color: `var(--${r.prediction.sentiment === 'positive' ? 'pos' : r.prediction.sentiment === 'negative' ? 'neg' : 'neu'})` }}>
                {r.prediction.sentiment}
              </div>
              <div className="small muted">top probability {pct(r.prediction.confidence)} · margin {pct(r.prediction.margin)}</div>
              {r.prediction.review_needed && <p className="warn small" style={{ marginTop: 6 }}>Low confidence: a person should read this text.</p>}
            </div>
            <ProbabilityBars p={{ positive: r.prediction.prob_positive, neutral: r.prediction.prob_neutral, negative: r.prediction.prob_negative }} />
            <div>
              <div className="label" style={{ marginBottom: 6 }}>Aspects</div>
              {r.aspects.length ? (
                <table className="table">
                  <thead><tr><th>Aspect</th><th>Clause</th><th>Clause sentiment</th></tr></thead>
                  <tbody>
                    {r.aspects.map((a: any) => (
                      <tr key={a.aspect_id}><td>{a.aspect}</td><td>{a.evidence}</td><td><Chip sentiment={a.sentiment} label={`${a.sentiment} ${pct(a.confidence)}`} /></td></tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="muted small">No teaching aspect detected.</p>
              )}
              {r.ambiguous.length > 0 && (
                <p className="small muted" style={{ marginTop: 8 }}>Ambiguous: {r.ambiguous.map((a: any) => `"${a.term}" (${a.aspect_label})`).join(', ')}</p>
              )}
            </div>
            <code className="mono small" style={{ display: 'block', background: 'var(--surface)', padding: 12, border: '1px solid var(--rule)' }}>{r.processed_text || '(empty)'}</code>
          </div>
        ) : (
          <Empty title="Try a sentence">Negation, contrast and multiple aspects in one comment are all handled. Results appear here.</Empty>
        )}
      </div>
    </div>
  )
}

export default function Explore() {
  const { datasetId, filters } = useApp()
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const [sort, setSort] = useState<'record' | 'negative' | 'positive' | 'uncertain'>('record')
  const [limit, setLimit] = useState(PAGE)
  const [open, setOpen] = useState<number | null>(params.get('review') ? Number(params.get('review')) : null)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 300)
    return () => clearTimeout(t)
  }, [q])
  useEffect(() => setLimit(PAGE), [debounced, sort, filters, datasetId])
  const list = useQuery({
    queryKey: ['reviews', datasetId, filters, debounced, sort, limit],
    queryFn: () => api.reviews(datasetId, filters, debounced, sort, 0, limit),
    placeholderData: keepPreviousData,
  })
  const pinned = params.get('review') ? Number(params.get('review')) : null
  const pinnedQ = useQuery({ queryKey: ['review', datasetId, pinned], queryFn: () => api.review(datasetId, pinned!), enabled: pinned !== null, retry: false })
  const ref = useReveal<HTMLDivElement>([list.data?.items.length, pinnedQ.data])
  const items = list.data?.items ?? []

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap">
          <div className="eyebrow" data-reveal>Explore</div>
          <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
            Read the <em>evidence,</em> review by review.
          </h1>
          <p className="lede" style={{ marginTop: 22 }} data-reveal>
            Every review with its predicted sentiment, the probabilities behind it, the aspects it mentions and the exact text the model saw.
          </p>
        </div>
      </section>

      {pinned !== null && pinnedQ.data && (
        <section className="section" style={{ paddingTop: 20 }}>
          <div className="wrap">
            <div className="label" style={{ marginBottom: 6 }}>Opened from the overview</div>
            <ReviewRow r={pinnedQ.data.review} open onToggle={() => (params.delete('review'), setParams(params))} />
          </div>
        </section>
      )}

      <section className="section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <SectionHead num="01" title="Reviews">
            {list.data ? `${list.data.total} reviews match the search within ${list.data.selection}.` : 'Loading reviews.'} Matched aspect words are underlined.
          </SectionHead>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', alignItems: 'end', marginBottom: 18 }} data-reveal>
            <label className="field" style={{ flex: '1 1 260px' }}>
              <span>Search review text</span>
              <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="assignment, pace, not clear" data-testid="search" />
            </label>
            <div className="field">
              <span>Sort</span>
              <Segmented label="Sort reviews" value={sort} onChange={setSort} options={[
                { value: 'record', label: 'Record order' },
                { value: 'negative', label: 'Most negative' },
                { value: 'positive', label: 'Most positive' },
                { value: 'uncertain', label: 'Least confident' },
              ]} />
            </div>
            <a className="btn ghost" href={api.exportUrl(datasetId, 'reviews.csv', filters)} download data-testid="download-csv">Download analysed CSV</a>
          </div>
          {list.error && <ErrorNote error={list.error} />}
          {list.isLoading && <Loading what="Loading reviews" />}
          {list.data && !items.length && <Empty title="No matching reviews">Try another search term or remove a filter.</Empty>}
          <div data-testid="review-list">
            {items.map((r) => (
              <ReviewRow key={r.record_id} r={r} open={open === r.record_id} onToggle={() => setOpen(open === r.record_id ? null : r.record_id)} />
            ))}
          </div>
          {list.data && items.length < list.data.total && (
            <div style={{ marginTop: 22 }}>
              <button type="button" className="btn ghost" onClick={() => setLimit(limit + PAGE)} data-testid="load-more">
                Show {Math.min(PAGE, list.data.total - items.length)} more of {list.data.total - items.length} remaining
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="02" title="Analyse a single comment">
            Type or paste one piece of feedback to see how the same pipeline reads it.
          </SectionHead>
          <Single />
        </div>
      </section>
    </div>
  )
}
