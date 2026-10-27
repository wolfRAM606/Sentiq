import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { SentimentStrip, StackBars, TrendBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Figure, Legend, Loading, SectionHead } from '../components/ui'
import { api } from '../lib/api'
import { fixed, pct, signed } from '../lib/format'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'
import { SentimentField } from '../three/SentimentField'

export default function Overview() {
  const { datasetId, filters, setFilters } = useApp()
  const nav = useNavigate()
  const q = useQuery({ queryKey: ['overview', datasetId, filters], queryFn: () => api.overview(datasetId, filters) })
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const ref = useReveal<HTMLDivElement>([q.data])
  const laneLabels = useMemo(() => Object.fromEntries((meta.data?.aspects ?? []).map((a) => [a.id, a.label])), [meta.data])
  const o = q.data
  const k = o?.kpis

  return (
    <div ref={ref}>
      <section className="hero">
        <div className="wrap hero-grid">
          <div>
            <div className="eyebrow" data-reveal>Course feedback intelligence</div>
            <h1 className="display" style={{ marginTop: 18 }} data-reveal data-delay="0.05">
              Every response <em>tells a story.</em>
            </h1>
            <p className="lede" style={{ marginTop: 26 }} data-reveal data-delay="0.12">
              Sentiq reads each review with spaCy, predicts its sentiment with a trained classifier and links what students say to
              specific teaching aspects, so every pattern on this page can be traced back to the comments behind it.
            </p>
            <div className="meta-line" data-reveal data-delay="0.18">
              <span>{o ? o.selection : 'Loading selection'}</span>
              <span>Logistic Regression and spaCy</span>
              <span>{o?.dataset.kind === 'demo' ? 'Synthetic demonstration data' : o?.dataset.name}</span>
            </div>
            {o?.dataset.kind === 'demo' && (
              <p className="notice demo small" style={{ marginTop: 22 }} data-reveal data-delay="0.22">
                You are viewing the bundled synthetic demonstration dataset, written for this project rather than collected from students.
                Upload your own CSV on the <a href="/data" onClick={(e) => (e.preventDefault(), nav('/data'))}>Data</a> page.
              </p>
            )}
          </div>
          <div data-reveal data-delay="0.1">
            {o && o.points.length > 0 ? (
              <SentimentField data={o.points} laneLabels={laneLabels} onPick={(id) => nav(`/explore?review=${id}`)} />
            ) : q.isLoading ? (
              <Loading what="Reading reviews" />
            ) : (
              <Empty title="Nothing to plot">No reviews match the current filters.</Empty>
            )}
          </div>
        </div>
      </section>

      {q.error && (
        <div className="wrap"><ErrorNote error={q.error} /></div>
      )}

      {k && k.valid_reviews === 0 && (
        <div className="wrap" style={{ paddingBottom: 80 }}>
          <Empty title="No reviews match the current filters">Remove a filter in the bar above to see results.</Empty>
        </div>
      )}

      {o && k && k.valid_reviews > 0 && (
        <>
          <section className="section">
            <div className="wrap">
              <SectionHead num="01" title="The numbers">
                Counts come from the trained classifier's predictions on the selected reviews. The feedback indicator is
                100 × (positive share + half the neutral share), a summary of expressed opinion.
              </SectionHead>
              <div className="figures">
                <Figure label="Feedback indicator" value={k.effectiveness} decimals={1} suffix="/ 100" tone="brand" note={`${k.valid_reviews} reviews in the selection`} />
                <Figure label="Positive" value={k.counts.positive} tone="positive" note={pct(k.shares.positive)} />
                <Figure label="Neutral" value={k.counts.neutral} tone="neutral" note={pct(k.shares.neutral)} />
                <Figure label="Negative" value={k.counts.negative} tone="negative" note={pct(k.shares.negative)} />
              </div>
              <div style={{ marginTop: 34 }} data-reveal>
                <SentimentStrip counts={k.counts} />
              </div>
              <div className="figures" style={{ marginTop: 34 }}>
                <Figure label="Reviews analysed" value={k.valid_reviews} note={`${o.total_records} records in file, ${k.excluded_records} excluded`} />
                <Figure label="Average sentiment score" value={k.avg_sentiment_score} decimals={2} prefix={k.avg_sentiment_score !== null && k.avg_sentiment_score >= 0 ? '+' : ''} note="P(positive) − P(negative), from −1 to +1" />
                <Figure label="Flagged for review" value={k.review_needed} tone="neutral" note={`${pct(k.review_needed / k.valid_reviews)} low-confidence predictions`} />
                <Figure label="Reviews with an aspect" value={k.with_aspect} note={pct(k.with_aspect / k.valid_reviews)} />
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="02" title={<>What students <em style={{ color: 'var(--brand)' }}>talk about</em></>}>
                Sentiment for each teaching aspect is predicted on the clause that mentions it, so one review can praise the lectures and
                criticise the assignments. Select an aspect to read its evidence.
              </SectionHead>
              <div className="split wide-left">
                <div data-reveal>
                  <Legend />
                  {o.aspects.length ? (
                    <StackBars
                      testid="aspect-bars"
                      rows={o.aspects.map((a) => ({
                        key: a.aspect_id,
                        label: a.aspect,
                        sub: `n=${a.reviews}`,
                        positive: a.positive,
                        neutral: a.neutral,
                        negative: a.negative,
                        value: pct(a.positive_share) + ' pos',
                        onClick: () => nav(`/aspects?focus=${a.aspect_id}`),
                      }))}
                    />
                  ) : (
                    <Empty title="No aspects detected">None of the selected reviews matched the teaching-aspect lexicon.</Empty>
                  )}
                </div>
                <div className="stack">
                  <div className="figure" data-reveal style={{ borderTop: '1px solid var(--rule)' }}>
                    <div className="label">Most positive aspect</div>
                    <div className="num-figure" style={{ fontSize: 30, margin: '10px 0 6px', color: 'var(--pos)' }} data-testid="most-positive">
                      {o.most_positive?.aspect ?? 'Not enough evidence'}
                    </div>
                    <div className="n">{o.most_positive ? `${o.most_positive.positive} of ${o.most_positive.reviews} mentions positive` : 'Needs at least 3 mentions'}</div>
                  </div>
                  <div className="figure" data-reveal>
                    <div className="label">Most negative aspect</div>
                    <div className="num-figure" style={{ fontSize: 30, margin: '10px 0 6px', color: 'var(--neg)' }} data-testid="most-negative">
                      {o.most_negative?.aspect ?? 'Not enough evidence'}
                    </div>
                    <div className="n">{o.most_negative ? `${o.most_negative.negative} of ${o.most_negative.reviews} mentions negative` : 'Needs at least 3 mentions'}</div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="03" title="What the feedback says">
                Each statement is generated from the numbers above by fixed rules, and every count can be checked on the detail pages.
              </SectionHead>
              <div className="rows" data-testid="insights">
                {o.insights.map((ins, i) => (
                  <div className="row" key={i} data-reveal data-delay={String(Math.min(i * 0.05, 0.3))}>
                    <div className="idx">{String(i + 1).padStart(2, '0')}</div>
                    <div className="body">{ins.text}</div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="04" title="Vocabulary and themes">
                Lemmatised keywords are counted once per review. Topics are discovered without supervision (NMF) and labelled by
                their top terms; the labels are automatic, not human-verified categories.
              </SectionHead>
              <div className="split">
                <div data-reveal>
                  <div className="label" style={{ marginBottom: 14 }}>Most frequent keywords</div>
                  {o.keywords.length ? (
                    <StackBars
                      mode="count"
                      rows={o.keywords.map((t) => ({
                        key: t.term, label: t.term, positive: t.positive, neutral: t.neutral, negative: t.negative, value: `${t.reviews}`,
                        onClick: () => nav(`/topics?term=${encodeURIComponent(t.term)}`),
                      }))}
                    />
                  ) : (
                    <Empty title="No recurring keywords">Keywords need to appear in at least two reviews.</Empty>
                  )}
                </div>
                <div data-reveal data-delay="0.1">
                  <div className="label" style={{ marginBottom: 14 }}>Discovered topics</div>
                  {o.topics.ok ? (
                    <div className="rows">
                      {o.topics.items.map((t, i) => (
                        <div key={t.topic_id} className="row clickable" onClick={() => nav('/topics#topics')}>
                          <div className="idx">T{i + 1}</div>
                          <div>
                            <div style={{ fontFamily: 'var(--font-display)', fontSize: 21 }}>{t.terms.slice(0, 3).join(' · ')}</div>
                            <div className="muted small" style={{ marginTop: 4 }}>
                              {t.n_reviews} reviews · {t.positive} positive, {t.neutral} neutral, {t.negative} negative
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty title="Topic discovery skipped">{o.topics.message}</Empty>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="wrap">
              <SectionHead num="05" title="Over time, and how much we could use">
                Dated reviews per period by predicted sentiment, and how much of the data each analysis could use.
              </SectionHead>
              <div className="split wide-left">
                <div data-reveal>
                  {o.trend.length ? (
                    <>
                      <Legend />
                      <TrendBars data={o.trend} />
                    </>
                  ) : (
                    <Empty title="No trend">Fewer than five reviews in the selection have a date.</Empty>
                  )}
                </div>
                <div className="rows" data-reveal data-delay="0.1">
                  <div className="row"><div className="idx">ALL</div><div>{o.total_records} records in the file, {k.valid_reviews + 0} valid in this selection.</div></div>
                  {Object.entries(o.exclusion_reasons).map(([reason, n]) => (
                    <div className="row" key={reason}><div className="idx">EXCL</div><div>{n} × {reason}</div></div>
                  ))}
                  <div className="row"><div className="idx">LEN</div><div>Average review length {fixed(k.avg_words, 0)} words (spaCy tokens).</div></div>
                  <div className="row"><div className="idx">AVG</div><div>Average sentiment score {signed(k.avg_sentiment_score)}.</div></div>
                </div>
              </div>
              <div style={{ marginTop: 40, display: 'flex', gap: 12, flexWrap: 'wrap' }} data-reveal>
                <button type="button" className="btn" onClick={() => nav('/insights')}>See recommendations</button>
                <button type="button" className="btn ghost" onClick={() => nav('/explore')}>Read the reviews</button>
                {filters.sentiment.length === 0 && (
                  <button type="button" className="btn ghost" onClick={() => setFilters({ sentiment: ['negative'] })}>Focus on negative feedback</button>
                )}
              </div>
              <div className="small muted" style={{ marginTop: 18 }}>
                Showing <Chip sentiment="positive" label={`${k.counts.positive} positive`} /> · <Chip sentiment="neutral" label={`${k.counts.neutral} neutral`} /> ·{' '}
                <Chip sentiment="negative" label={`${k.counts.negative} negative`} />
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
