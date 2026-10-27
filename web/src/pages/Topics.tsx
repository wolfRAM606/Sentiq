import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { StackBars, ValueBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Highlight, Legend, Loading, SectionHead, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

export default function Topics() {
  const { datasetId, filters } = useApp()
  const [params] = useSearchParams()
  const [n, setN] = useState<1 | 2>(1)
  const [minReviews, setMinReviews] = useState(2)
  const [top, setTop] = useState(15)
  const [hide, setHide] = useState(true)
  const [term, setTerm] = useState<string | null>(params.get('term'))
  const [k, setK] = useState(4)
  const kw = useQuery({
    queryKey: ['keywords', datasetId, filters, n, minReviews, hide, top],
    queryFn: () => api.keywords(datasetId, filters, n, minReviews, hide, top),
    placeholderData: keepPreviousData,
  })
  useEffect(() => {
    if (kw.data && kw.data.all_terms.length && (!term || !kw.data.all_terms.includes(term))) setTerm(kw.data.all_terms[0])
  }, [kw.data, term])
  const tr = useQuery({ queryKey: ['termReviews', datasetId, filters, term, n], queryFn: () => api.keywordReviews(datasetId, filters, term!, n), enabled: !!term })
  const tp = useQuery({ queryKey: ['topics', datasetId, filters, k], queryFn: () => api.topics(datasetId, filters, k), placeholderData: keepPreviousData })
  const ref = useReveal<HTMLDivElement>()
  useEffect(() => {
    if (window.location.hash === '#topics') setTimeout(() => document.getElementById('topics')?.scrollIntoView({ block: 'start' }), 300)
  }, [])
  const terms = kw.data?.terms ?? []
  const leaning = (dir: 1 | -1) =>
    terms
      .filter((t) => t.reviews >= Math.max(2, minReviews) && (dir > 0 ? t.positive > 0 : t.negative > 0))
      .sort((a, b) => dir * (b.net_sentiment - a.net_sentiment) || b.reviews - a.reviews)
      .slice(0, 6)

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap">
          <div className="eyebrow" data-reveal>Topics and keywords</div>
          <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
            The <em>vocabulary</em> of student feedback.
          </h1>
          <p className="lede" style={{ marginTop: 22 }} data-reveal>
            Lemmatised keywords and noun phrases from spaCy, split by predicted sentiment, and topics discovered without supervision. Everything is
            computed from the active dataset and selection{kw.data ? ` (${kw.data.selection})` : ''}.
          </p>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <SectionHead num="01" title="Keywords">Counted once per review, so one long comment cannot dominate.</SectionHead>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'end', marginBottom: 24 }} data-reveal>
            <div className="field"><span>Terms</span>
              <Segmented label="Term length" value={String(n) as '1' | '2'} onChange={(v) => setN(Number(v) as 1 | 2)}
                options={[{ value: '1', label: 'Single words' }, { value: '2', label: 'Two-word phrases' }]} />
            </div>
            <label className="field" style={{ width: 150 }}><span>Min. reviews</span>
              <input className="input" type="number" min={1} max={50} value={minReviews} data-testid="min-reviews"
                onChange={(e) => setMinReviews(Math.max(1, Number(e.target.value) || 1))} />
            </label>
            <label className="field" style={{ width: 220 }}><span>Show top {top}</span>
              <input type="range" min={5} max={40} value={top} onChange={(e) => setTop(Number(e.target.value))} data-testid="top-n" />
            </label>
            <button type="button" className="check" aria-pressed={hide} onClick={() => setHide(!hide)} data-testid="hide-generic">
              Hide generic words (teacher, class, course)
            </button>
          </div>
          {kw.error && <ErrorNote error={kw.error} />}
          {kw.isLoading && <Loading />}
          {kw.data && (terms.length ? (
            <div className="split wide-left">
              <div data-reveal>
                <Legend />
                <StackBars mode="count" testid="keyword-bars"
                  rows={terms.map((t) => ({ key: t.term, label: t.term, positive: t.positive, neutral: t.neutral, negative: t.negative, value: String(t.reviews), onClick: () => setTerm(t.term) }))} />
                <p className="small muted" style={{ marginTop: 10 }}>{kw.data.total_terms} terms meet the minimum. Select a term to read its reviews.</p>
              </div>
              <div className="stack" data-reveal data-delay="0.1">
                <div>
                  <div className="label" style={{ marginBottom: 8 }}>Leaning positive</div>
                  <table className="table"><tbody>{leaning(1).map((t) => <tr key={t.term}><td>{t.term}</td><td className="num">{t.positive} pos / {t.negative} neg</td></tr>)}</tbody></table>
                </div>
                <div>
                  <div className="label" style={{ marginBottom: 8 }}>Leaning negative</div>
                  <table className="table"><tbody>{leaning(-1).map((t) => <tr key={t.term}><td>{t.term}</td><td className="num">{t.positive} pos / {t.negative} neg</td></tr>)}</tbody></table>
                </div>
              </div>
            </div>
          ) : (
            <Empty title="No recurring terms">Lower the minimum or remove a filter.</Empty>
          ))}
        </div>
      </section>

      {term && (
        <section className="section">
          <div className="wrap">
            <SectionHead num="02" title={<>Reviews containing <em style={{ color: 'var(--brand)' }}>"{term}"</em></>}>
              {tr.data ? `${tr.data.total} reviews contain this term; up to 8 are shown.` : 'Loading.'}
            </SectionHead>
            <div data-testid="term-reviews">
              {tr.data?.items.map((r) => (
                <article className="review" key={r.record_id} data-reveal>
                  <div className="text"><Highlight text={r.review_text} terms={term.split(' ')} /></div>
                  <div className="meta"><Chip sentiment={r.sentiment} /><span className="mono">#{r.record_id}</span>{r.course && <span>{r.course}</span>}</div>
                </article>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="section">
        <div className="wrap">
          <SectionHead num="03" title="Noun phrases">spaCy noun chunks, lemmatised, with determiners and pronouns removed, appearing in at least two reviews.</SectionHead>
          {kw.data?.noun_phrases.length ? (
            <div data-reveal>
              <ValueBars rows={kw.data.noun_phrases.map((p) => ({ key: p.phrase, label: p.phrase, value: p.reviews }))} />
            </div>
          ) : <Empty title="No recurring noun phrases">Noun phrases need to appear in at least two reviews.</Empty>}
        </div>
      </section>

      <section className="section" id="topics">
        <div className="wrap">
          <SectionHead num="04" title="Discovered topics">
            TF-IDF and non-negative matrix factorisation on spaCy content lemmas. Each review is assigned to its dominant topic. Labels are the top terms,
            generated automatically, not human-verified categories.
          </SectionHead>
          <label className="field" style={{ maxWidth: 340, marginBottom: 26 }} data-reveal>
            <span>Number of topics: {k}</span>
            <input type="range" min={2} max={8} value={k} onChange={(e) => setK(Number(e.target.value))} data-testid="topic-k" />
          </label>
          {tp.error && <ErrorNote error={tp.error} />}
          {tp.data && !tp.data.ok && <Empty title="Topic discovery is not available for this selection">{tp.data.message}</Empty>}
          {tp.data?.ok && (
            <>
              <p className="small muted" style={{ marginBottom: 14 }} data-testid="topic-message">
                {tp.data.message}{tp.data.unassigned ? ` ${tp.data.unassigned} reviews had no informative terms and are unassigned.` : ''}
              </p>
              <div className="rows" data-testid="topic-list">
                {tp.data.items.map((t, i) => (
                  <details className="row" key={`${k}-${t.topic_id}`} style={{ display: 'block' }} data-reveal>
                    <summary style={{ cursor: 'pointer', listStyle: 'none', display: 'grid', gridTemplateColumns: '56px minmax(0,1fr) auto', gap: 16, alignItems: 'baseline' }}>
                      <span className="idx">T{i + 1}</span>
                      <span style={{ fontFamily: 'var(--font-display)', fontSize: 24 }}>{t.terms.slice(0, 4).join(' · ')}</span>
                      <span className="small muted" data-testid="topic-n">{t.n_reviews} reviews</span>
                    </summary>
                    <div className="split" style={{ marginTop: 18 }}>
                      <div>
                        <div className="label" style={{ marginBottom: 8 }}>Term weights</div>
                        <ValueBars color="var(--brand)" rows={t.terms.map((term, j) => ({ key: term, label: term, value: t.weights[j] }))} format={(v) => v.toFixed(2)} />
                        <p className="small muted" style={{ marginTop: 8 }}>{t.positive} positive, {t.neutral} neutral, {t.negative} negative</p>
                      </div>
                      <div>
                        <div className="label" style={{ marginBottom: 8 }}>Most representative reviews</div>
                        {t.representatives.map((r) => (
                          <div className="review" key={r.record_id} style={{ padding: '12px 0' }}>
                            <div style={{ fontSize: 16 }}><Highlight text={r.review_text} terms={t.terms.slice(0, 5)} /></div>
                            <div className="meta"><Chip sentiment={r.sentiment} /><span className="mono">#{r.record_id}</span></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
