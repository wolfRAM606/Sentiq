import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { IndicatorScale, StackBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Legend, Loading, SectionHead, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { fixed, pct } from '../lib/format'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

export default function Insights() {
  const { datasetId, filters } = useApp()
  const [groupBy, setGroupBy] = useState('course')
  const [kind, setKind] = useState<'all' | 'issue' | 'strength'>('all')
  const q = useQuery({ queryKey: ['effectiveness', datasetId, filters, groupBy], queryFn: () => api.effectiveness(datasetId, filters, groupBy) })
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const ref = useReveal<HTMLDivElement>()
  const e = q.data
  const c = e?.counts
  const n = e?.reviews ?? 0
  const minMentions = meta.data?.limits.min_aspect_mentions ?? 3
  const groupMin = meta.data?.limits.group_min ?? 15
  const recs = (e?.recommendations ?? []).filter((r) => kind === 'all' || r.kind === kind)

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap hero-grid">
          <div>
            <div className="eyebrow" data-reveal>Effectiveness insights</div>
            <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
              From opinions to <em>actionable</em> evidence.
            </h1>
          </div>
          <div data-reveal data-delay="0.1">
            <div className="label">Sentiment-derived feedback indicator</div>
            <div className="num-figure" style={{ fontSize: 'clamp(64px, 9vw, 120px)', color: 'var(--brand)', lineHeight: 1 }} data-testid="indicator">
              {e ? fixed(e.indicator, 1) : '...'}<span style={{ fontSize: 22, color: 'var(--muted)' }}> / 100</span>
            </div>
            <p className="muted" style={{ marginTop: 10 }}>{e ? `${e.selection}. ` : ''}It summarises expressed opinion and should be read alongside other evidence about teaching.</p>
          </div>
        </div>
      </section>

      {q.isLoading && <div className="wrap"><Loading /></div>}
      {q.error && <div className="wrap"><ErrorNote error={q.error} /></div>}
      {e && n === 0 && <div className="wrap" style={{ paddingBottom: 80 }}><Empty title="No reviews match the current filters">Remove a filter to see results.</Empty></div>}

      {e && c && n > 0 && (
        <>
          <section className="section" style={{ paddingTop: 40 }}>
            <div className="wrap">
              <SectionHead num="01" title="How the indicator is calculated">
                A 50/50 weighting of the positive share and the negative complement. Because the three shares add up to one, the two forms are the same.
              </SectionHead>
              <div className="split">
                <div data-reveal>
                  <p className="quote" style={{ fontSize: 'clamp(20px, 2.2vw, 28px)', fontStyle: 'normal' }}>
                    Indicator = 100 × (p<sub>pos</sub> + ½ p<sub>neu</sub>)
                    <br />= 50 p<sub>pos</sub> + 50 (1 − p<sub>neg</sub>)
                  </p>
                  <p style={{ marginTop: 18 }} data-testid="formula">
                    With <strong>{c.positive}</strong> positive, <strong>{c.neutral}</strong> neutral and <strong>{c.negative}</strong> negative predictions out of{' '}
                    <strong>{n}</strong> reviews: 100 × ({c.positive}/{n} + 0.5 × {c.neutral}/{n}) = <strong>{fixed(e.indicator, 1)}</strong>.
                  </p>
                  <p className="small muted" style={{ marginTop: 12 }}>
                    A weighting of 70% positive and 30% negative complement would give 100 × (p + 0.3 u) instead, scoring all-neutral feedback at 30 rather than
                    the midpoint of 50, so the symmetric form is used.
                  </p>
                </div>
                <div data-reveal data-delay="0.1">
                  <IndicatorScale value={e.indicator} />
                  {e.small_sample && (
                    <p className="notice demo" style={{ marginTop: 22 }} role="status" data-testid="small-sample">
                      Minimum-sample warning: only {n} reviews are in the selection (recommended at least {meta.data?.limits.min_sample_warning ?? 30}).
                      The indicator can change substantially with a few more reviews.
                    </p>
                  )}
                  <p className="notice" style={{ marginTop: 22 }}>
                    Interpret with care. Student feedback may be biased, incomplete or unrepresentative, and the sentiment model makes errors (see the Model page).
                    This indicator describes expressed opinion and must not be used on its own for evaluation decisions.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="02" title="Aspect-level indicators">Shown only for aspects with at least {minMentions} mentioning reviews.</SectionHead>
              {e.aspects.filter((a) => a.enough_evidence).length ? (
                <div data-reveal>
                  <Legend />
                  <StackBars rows={e.aspects.filter((a) => a.enough_evidence).map((a) => ({
                    key: a.aspect_id, label: a.aspect, sub: `n=${a.reviews}`, positive: a.positive, neutral: a.neutral, negative: a.negative,
                    value: a.aspect_score !== null ? `${a.aspect_score.toFixed(0)}/100` : 'n/a',
                  }))} />
                </div>
              ) : <Empty title="Not enough aspect evidence">No aspect has {minMentions} or more mentions in this selection.</Empty>}
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="03" title="Breakdown by group">
                Indicators are withheld for groups with fewer than {groupMin} reviews. Groups are listed alphabetically, not ranked, and differences are descriptive only.
              </SectionHead>
              {e.group_options.length ? (
                <>
                  <div style={{ marginBottom: 18 }} data-reveal>
                    <Segmented label="Group by" value={groupBy} onChange={setGroupBy}
                      options={e.group_options.map((g) => ({ value: g, label: g.charAt(0).toUpperCase() + g.slice(1) }))} />
                  </div>
                  <div className="table-wrap" data-reveal>
                    <table className="table" data-testid="groups">
                      <thead><tr><th>{groupBy}</th><th className="num">Reviews</th><th className="num">Positive</th><th className="num">Neutral</th><th className="num">Negative</th><th className="num">Indicator</th><th>Evidence</th></tr></thead>
                      <tbody>
                        {e.groups.map((g) => (
                          <tr key={g.group}>
                            <td>{g.group}</td><td className="num">{g.reviews}</td><td className="num">{g.positive}</td><td className="num">{g.neutral}</td><td className="num">{g.negative}</td>
                            <td className="num">{g.indicator === null ? <span className="muted">withheld</span> : g.indicator.toFixed(1)}</td>
                            <td>{g.evidence}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : <Empty title="No groups">The dataset has no course, instructor or semester column.</Empty>}
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="04" title="Evidence-linked recommendations">
                Generated by fixed rules: an issue needs at least {minMentions} negative mentions and a 35% negative share; a strength needs at least {minMentions} positive mentions
                and a 60% positive share. Sentiq does not suggest anything the data does not support.
              </SectionHead>
              <div style={{ marginBottom: 18 }} data-reveal>
                <Segmented label="Show recommendations" value={kind} onChange={setKind} options={[
                  { value: 'all', label: `All (${e.recommendations.length})` },
                  { value: 'issue', label: `Issues (${e.recommendations.filter((r) => r.kind === 'issue').length})` },
                  { value: 'strength', label: `Strengths (${e.recommendations.filter((r) => r.kind === 'strength').length})` },
                ]} />
              </div>
              {recs.length ? (
                <div className="rows" data-testid="recommendations">
                  {recs.map((r, i) => (
                    <article className="row" key={r.aspect_id + r.kind} style={{ gridTemplateColumns: '56px minmax(0,1fr)' }} data-reveal data-delay={String(Math.min(i * 0.04, 0.2))}>
                      <div className="idx">{String(i + 1).padStart(2, '0')}</div>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap', alignItems: 'baseline' }}>
                          <h3 style={{ fontSize: 26 }}>{r.headline}</h3>
                          <Chip sentiment={r.kind === 'issue' ? 'negative' : 'positive'} label={r.priority === 'high' ? 'High priority' : r.priority === 'medium' ? 'Worth attention' : 'Strength'} />
                        </div>
                        <p style={{ marginTop: 10, maxWidth: '78ch' }}><strong>Suggested action:</strong> {r.action}</p>
                        <div style={{ marginTop: 12 }}>
                          {r.examples.map((x) => (
                            <p key={x.record_id} className="quote" style={{ fontSize: 17, margin: '6px 0 6px 18px', color: 'var(--muted)' }}>
                              "{x.evidence}" <span className="mono small" style={{ fontStyle: 'normal' }}>review #{x.record_id}</span>
                            </p>
                          ))}
                        </div>
                        <p className="small muted" style={{ marginTop: 10 }}>
                          Evidence: {r.supporting_reviews} of {r.aspect_reviews} reviews mentioning {r.aspect} ({pct(r.share)}). {r.caveats.join(' ')}
                        </p>
                      </div>
                    </article>
                  ))}
                </div>
              ) : <Empty title="No recommendation meets the evidence thresholds">Sentiq only suggests actions the data supports.</Empty>}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
