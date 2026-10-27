import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { StackBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Highlight, Legend, Loading, SectionHead } from '../components/ui'
import { api } from '../lib/api'
import { pct } from '../lib/format'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

export default function Aspects() {
  const { datasetId, filters } = useApp()
  const [params, setParams] = useSearchParams()
  const q = useQuery({ queryKey: ['aspects', datasetId, filters], queryFn: () => api.aspects(datasetId, filters) })
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const summary = q.data?.summary ?? []
  const [selected, setSelected] = useState<string | null>(params.get('focus'))
  const [clause, setClause] = useState<string[]>([])
  useEffect(() => {
    if (summary.length && (!selected || !summary.some((s) => s.aspect_id === selected))) setSelected(summary[0].aspect_id)
  }, [summary, selected])
  const ev = useQuery({
    queryKey: ['evidence', datasetId, filters, selected, clause],
    queryFn: () => api.evidence(datasetId, selected!, filters, clause),
    enabled: !!selected,
  })
  const ref = useReveal<HTMLDivElement>([q.data, ev.data])
  const row = summary.find((s) => s.aspect_id === selected)
  const choose = (id: string) => {
    setSelected(id)
    setClause([])
    params.set('focus', id) // not 'aspect', which is the global aspect filter
    setParams(params, { replace: true })
    document.getElementById('evidence')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const minMentions = meta.data?.limits.min_aspect_mentions ?? 3

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap hero-grid">
          <div>
            <div className="eyebrow" data-reveal>Aspects</div>
            <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
              What exactly are students <em>talking about?</em>
            </h1>
          </div>
          <div data-reveal data-delay="0.1">
            <p className="lede">
              A transparent, rule-assisted component: spaCy sentences and clauses are matched against a configurable taxonomy of twelve
              teaching aspects, and sentiment is predicted for the clause that triggered each match. It is not a trained aspect model, so no
              aspect-level accuracy is claimed.
            </p>
            {q.data && (
              <p className="meta-line" style={{ marginTop: 18 }} data-testid="aspect-coverage">
                <span>{q.data.with_aspect} of {q.data.reviews} reviews matched an aspect</span>
                <span>{q.data.unmatched.length} unmatched</span>
                <span>{new Set(q.data.ambiguous.map((a: any) => a.record_id)).size} with ambiguous words</span>
              </p>
            )}
          </div>
        </div>
      </section>

      {q.isLoading && <div className="wrap"><Loading /></div>}
      {q.error && <div className="wrap"><ErrorNote error={q.error} /></div>}

      {q.data && (
        <>
          <section className="section" style={{ paddingTop: 40 }}>
            <div className="wrap">
              <SectionHead num="01" title="The aspect index">
                Share of positive, neutral and negative clauses per aspect, with the number of mentioning reviews. Select an aspect to read its evidence.
              </SectionHead>
              {summary.length ? (
                <div data-reveal>
                  <Legend />
                  <StackBars
                    testid="aspect-index"
                    rows={summary.map((a) => ({
                      key: a.aspect_id,
                      label: <span style={{ color: a.aspect_id === selected ? 'var(--brand)' : undefined }}>{a.aspect}</span>,
                      sub: `n=${a.reviews}`,
                      positive: a.positive,
                      neutral: a.neutral,
                      negative: a.negative,
                      value: a.enough_evidence && a.aspect_score !== null ? `${a.aspect_score.toFixed(0)}/100` : 'few',
                      onClick: () => choose(a.aspect_id),
                    }))}
                  />
                  <p className="small muted" style={{ marginTop: 12 }}>
                    Right-hand value: the aspect indicator, 100 × (positive + half neutral share), shown only with at least {minMentions} mentions.
                  </p>
                </div>
              ) : (
                <Empty title="No aspects detected">None of the selected reviews matched the lexicon.</Empty>
              )}
            </div>
          </section>

          {row && (
            <section className="section" id="evidence">
              <div className="wrap">
                <SectionHead num="02" title={row.aspect}>
                  {meta.data?.aspects.find((a) => a.id === row.aspect_id)?.description}
                </SectionHead>
                <div className="figures" data-reveal>
                  <div className="figure"><div className="label">Mentioning reviews</div><div className="v num-figure" data-testid="ev-n">{row.reviews}</div><div className="n">{pct(row.coverage)} of the selection</div></div>
                  <div className="figure"><div className="label">Positive</div><div className="v num-figure" style={{ color: 'var(--pos)' }}>{row.positive}</div><div className="n">{pct(row.positive_share)}</div></div>
                  <div className="figure"><div className="label">Neutral</div><div className="v num-figure" style={{ color: 'var(--neu)' }}>{row.neutral}</div></div>
                  <div className="figure"><div className="label">Negative</div><div className="v num-figure" style={{ color: 'var(--neg)' }}>{row.negative}</div><div className="n">{pct(row.negative_share)}</div></div>
                </div>
                {!row.enough_evidence && (
                  <p className="notice demo" style={{ marginTop: 18 }}>Fewer than {minMentions} reviews mention this aspect, which is too little evidence for conclusions.</p>
                )}
                <div style={{ margin: '28px 0 8px', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <span className="label" style={{ marginRight: 8 }}>Clause sentiment</span>
                  {['positive', 'neutral', 'negative'].map((s) => (
                    <button key={s} type="button" className="check" aria-pressed={clause.includes(s)} data-testid={`clause-${s}`}
                      onClick={() => setClause(clause.includes(s) ? clause.filter((c) => c !== s) : [...clause, s])}>
                      {s}
                    </button>
                  ))}
                  <span className="small muted" style={{ marginLeft: 8 }}>{ev.data ? `${ev.data.items.length} evidence clauses` : ''}</span>
                </div>
                {ev.isLoading && <Loading />}
                <div data-testid="evidence-list">
                  {ev.data?.items.map((m) => (
                    <details className="review" key={m.record_id}>
                      <summary style={{ cursor: 'pointer', listStyle: 'none' }}>
                        <div className="quote">"<Highlight text={m.evidence} terms={m.terms.split(',').map((t) => t.trim())} />"</div>
                        <div className="meta">
                          <Chip sentiment={m.aspect_sentiment} label={`${m.aspect_sentiment} ${pct(m.aspect_confidence)}`} />
                          {m.aspect_review_needed && <span className="warn">Review needed</span>}
                          <span>{m.match_type}{m.negated ? ' · negated' : ''}</span>
                          <span className="mono">#{m.record_id}</span>
                          <span className="link-btn">Full review</span>
                        </div>
                      </summary>
                      <div style={{ marginTop: 12, borderLeft: '1px solid var(--rule)', paddingLeft: 16 }}>
                        <p>{m.review_text}</p>
                        <p className="small muted" style={{ marginTop: 6 }}>
                          Whole-review prediction: {m.review_sentiment} ({pct(m.review_confidence)}). The aspect sentiment above is predicted for the quoted clause only.
                        </p>
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            </section>
          )}

          <section className="section">
            <div className="wrap">
              <SectionHead num="03" title="What did not match">
                Unmatched reviews contain no aspect term and no general comment on the teacher or course; they are counted as "no aspect detected",
                which is reported separately from neutral sentiment. Ambiguous words only count when a supporting context word appears nearby.
              </SectionHead>
              <div className="split">
                <div data-reveal>
                  <div className="label" style={{ marginBottom: 10 }}>Unmatched reviews ({q.data.unmatched.length})</div>
                  {q.data.unmatched.length ? (
                    <div className="rows" data-testid="unmatched">
                      {q.data.unmatched.map((r) => (
                        <div className="row" key={r.record_id}><div className="idx">#{r.record_id}</div><div style={{ fontSize: 16 }}>{r.review_text} <Chip sentiment={r.sentiment} /></div></div>
                      ))}
                    </div>
                  ) : <Empty title="None">Every review matched at least one aspect.</Empty>}
                </div>
                <div data-reveal data-delay="0.1">
                  <div className="label" style={{ marginBottom: 10 }}>Ambiguous words ({q.data.ambiguous.length})</div>
                  {q.data.ambiguous.length ? (
                    <table className="table" data-testid="ambiguous">
                      <thead><tr><th>#</th><th>Word</th><th>Possible aspect</th></tr></thead>
                      <tbody>{q.data.ambiguous.map((a: any, i: number) => <tr key={i}><td className="mono">{a.record_id}</td><td>{a.term}</td><td>{a.aspect_label}</td></tr>)}</tbody>
                    </table>
                  ) : <Empty title="None">No ambiguous candidate words in the selection.</Empty>}
                </div>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="04" title="The taxonomy">
                Loaded from config/aspect_taxonomy.json. Editing that file changes the analysis on the next request, with no restart.
              </SectionHead>
              <div className="rows" data-testid="taxonomy">
                {meta.data?.aspects.map((a, i) => (
                  <div className="row" key={a.id} data-reveal>
                    <div className="idx">{String(i + 1).padStart(2, '0')}</div>
                    <div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: 22 }}>{a.label}</div>
                      <p className="muted small" style={{ marginTop: 4 }}>{a.description}</p>
                      <p className="small" style={{ marginTop: 8 }}><span className="label">Terms</span> {a.terms.join(', ')}</p>
                      {a.phrases.length > 0 && <p className="small" style={{ marginTop: 4 }}><span className="label">Phrases</span> {a.phrases.join(', ')}</p>}
                      {a.context_terms.length > 0 && <p className="small" style={{ marginTop: 4 }}><span className="label">Need context</span> {a.context_terms.join(', ')}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
