import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { GroupedBars, ProbabilityBars, ReliabilityChart, ValueBars } from '../charts/Charts'
import { Chip, Empty, ErrorNote, Loading, SectionHead, Segmented } from '../components/ui'
import { api } from '../lib/api'
import { fixed, pct } from '../lib/format'
import { useReveal } from '../lib/motion'
import { ConfusionTower } from '../three/ConfusionTower'

export default function Model() {
  const q = useQuery({ queryKey: ['model'], queryFn: api.model, staleTime: Infinity })
  const ref = useReveal<HTMLDivElement>()
  const [cls, setCls] = useState<'positive' | 'neutral' | 'negative'>('positive')
  const [errFilter, setErrFilter] = useState<'all' | 'positive' | 'neutral' | 'negative'>('all')
  const [text, setText] = useState('The teacher explains well but the exams are not fair.')
  const tryIt = useMutation({ mutationFn: (t: string) => api.analyzeText(t) })
  const r = q.data
  if (!r)
    return (
      <div ref={ref} className="wrap" style={{ padding: '80px 0' }}>
        {q.error ? <ErrorNote error={q.error} /> : <Loading what="Loading the training report" />}
      </div>
    )
  const models = r.models as Record<string, any>
  const lr = models[r.primary_model]
  const test = lr.test
  const labels: string[] = test.labels
  const clean = r.dataset.cleaning
  const errors = (r.misclassified_examples as any[]).filter((e) => errFilter === 'all' || e.true === errFilter)

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap hero-grid">
          <div>
            <div className="eyebrow" data-reveal>Model</div>
            <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
              A classifier you can <em>inspect.</em>
            </h1>
            <p className="lede" style={{ marginTop: 22 }} data-reveal>
              spaCy preprocessing, TF-IDF features and Logistic Regression, compared with three baselines. Every number below is read from the saved training
              report; the held-out test set was scored once, after tuning on the training split.
            </p>
          </div>
          <div data-reveal data-delay="0.1">
            <div className="label">Held-out macro-F1, Logistic Regression</div>
            <div className="num-figure" style={{ fontSize: 'clamp(64px, 9vw, 120px)', color: 'var(--brand)', lineHeight: 1 }} data-testid="macro-f1">{fixed(test.macro_f1, 3)}</div>
            <p className="muted" style={{ marginTop: 10 }}>
              Accuracy {fixed(test.accuracy, 3)} on {r.split.test_rows} unseen comments. Majority-class baseline macro-F1 {fixed(models.majority_baseline.test.macro_f1, 3)}.
              Trained {r.trained_at}.
            </p>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <SectionHead num="01" title="Where the model is right and wrong">
            The held-out confusion matrix in three dimensions. Rows are the true labels and columns the predictions; the diagonal is correct.
          </SectionHead>
          <div className="split wide-left">
            <div data-reveal><ConfusionTower cm={test.confusion_matrix} labels={labels} /></div>
            <div data-reveal data-delay="0.1">
              <table className="table" data-testid="confusion-table">
                <thead><tr><th>True \ predicted</th>{labels.map((l) => <th key={l} className="num">{l}</th>)}</tr></thead>
                <tbody>{(test.confusion_matrix as number[][]).map((row, i) => (
                  <tr key={labels[i]}><td>{labels[i]}</td>{row.map((v, j) => <td key={j} className="num" style={{ fontWeight: i === j ? 600 : 400 }}>{v}</td>)}</tr>
                ))}</tbody>
              </table>
              <p className="notice demo" style={{ marginTop: 22 }}>
                The neutral class is small ({clean.clean_label_counts.neutral} examples in total, {test.per_class.neutral.support} in the test set) and loosely defined in the source data,
                so neutral F1 is low ({fixed(test.per_class.neutral.f1, 2)}). Positive and negative are separated much better. Treat neutral predictions with particular caution.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="02" title="Compared with the baselines">
            Cross-validated macro-F1 on training folds, used for tuning, next to held-out scores, reported only. Logistic Regression was chosen as the primary model in
            advance because it gives class probabilities; switching to whichever scores best on the test set would leak test information into model selection.
          </SectionHead>
          <div data-reveal>
            <GroupedBars
              series={[{ name: 'CV macro-F1 (train folds)', color: 'var(--sage)' }, { name: 'Test macro-F1', color: 'var(--brand)' }, { name: 'Test accuracy', color: 'var(--surface-2)' }]}
              groups={Object.entries(models).map(([key, m]) => ({ key, label: m.display_name, values: [m.cv_macro_f1_mean, m.test.macro_f1, m.test.accuracy] }))}
            />
          </div>
          <div className="table-wrap" style={{ marginTop: 34 }} data-reveal>
            <table className="table" data-testid="model-table">
              <thead><tr><th>Model</th><th className="num">CV macro-F1</th><th className="num">± std</th><th className="num">Test accuracy</th><th className="num">Test macro-F1</th><th>Chosen settings</th></tr></thead>
              <tbody>{Object.entries(models).map(([key, m]) => (
                <tr key={key}>
                  <td>{m.display_name}</td><td className="num">{fixed(m.cv_macro_f1_mean, 3)}</td><td className="num">{fixed(m.cv_macro_f1_std, 3)}</td>
                  <td className="num">{fixed(m.test.accuracy, 3)}</td><td className="num">{fixed(m.test.macro_f1, 3)}</td>
                  <td className="mono small">{Object.entries(m.best_params).map(([k, v]) => `${k.split('__').pop()}=${JSON.stringify(v)}`).join(', ')}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="03" title="Per class, and how far to trust a probability">
            Precision, recall and F1 for each class; then calibration: does a 70% top probability come with about 70% accuracy?
          </SectionHead>
          <div className="split">
            <div data-reveal>
              <GroupedBars
                series={[{ name: 'Precision', color: 'var(--sage)' }, { name: 'Recall', color: 'var(--brand)' }, { name: 'F1', color: 'var(--neu-fill)' }]}
                groups={['positive', 'neutral', 'negative'].map((l) => ({ key: l, label: <Chip sentiment={l} />, values: [test.per_class[l].precision, test.per_class[l].recall, test.per_class[l].f1] }))}
              />
            </div>
            <div data-reveal data-delay="0.1">
              <ReliabilityChart bins={r.calibration.bins} />
              <p className="small muted" style={{ marginTop: 8 }} data-testid="ece">
                Expected calibration error {fixed(r.calibration.ece, 3)} (0 is perfect). No post-hoc calibration is applied, so probabilities are shown as model estimates.
                Predictions under 55% top probability, or within 15 points of the runner-up, are flagged for review.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="04" title="What the model learned">The largest Logistic Regression weights per class: TF-IDF n-grams of spaCy lemmas, including neg_ negation features.</SectionHead>
          <div style={{ marginBottom: 18 }} data-reveal>
            <Segmented label="Class" value={cls} onChange={setCls} options={[{ value: 'positive', label: 'Positive' }, { value: 'neutral', label: 'Neutral' }, { value: 'negative', label: 'Negative' }]} />
          </div>
          <div data-reveal data-testid="features">
            <ValueBars color="var(--brand)" format={(v) => v.toFixed(2)} rows={(r.top_features[cls] as any[]).map((f) => ({ key: f.feature, label: <span className="mono">{f.feature}</span>, value: f.weight }))} />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="05" title="Mistakes worth reading">
            {r.misclassified_total} of {r.split.test_rows} test comments were misclassified. The most confident mistakes come first; they often reveal label noise, or suggestions the model cannot read.
          </SectionHead>
          <div style={{ marginBottom: 18 }} data-reveal>
            <Segmented label="True label" value={errFilter} onChange={setErrFilter} options={[
              { value: 'all', label: 'All' }, { value: 'positive', label: 'True positive' }, { value: 'neutral', label: 'True neutral' }, { value: 'negative', label: 'True negative' },
            ]} />
          </div>
          <div className="table-wrap" data-reveal>
            <table className="table" data-testid="errors">
              <thead><tr><th>Comment</th><th>True</th><th>Predicted</th><th className="num">P(pos)</th><th className="num">P(neu)</th><th className="num">P(neg)</th></tr></thead>
              <tbody>{errors.map((e, i) => (
                <tr key={i}>
                  <td>{e.text}</td><td><Chip sentiment={e.true} /></td><td><Chip sentiment={e.predicted} /></td>
                  <td className="num">{pct(e.probabilities.positive)}</td><td className="num">{pct(e.probabilities.neutral)}</td><td className="num">{pct(e.probabilities.negative)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="06" title="Try the model">A prediction on new, unlabelled text. It is separate from the held-out evaluation above.</SectionHead>
          <div className="split">
            <div data-reveal>
              <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} data-testid="try-text" />
              <button type="button" className="btn" style={{ marginTop: 12 }} onClick={() => tryIt.mutate(text)} disabled={tryIt.isPending} data-testid="try-run">Classify</button>
              {tryIt.error && <div style={{ marginTop: 12 }}><ErrorNote error={tryIt.error} /></div>}
            </div>
            <div data-reveal data-delay="0.1" data-testid="try-result">
              {tryIt.data ? (
                <>
                  <p style={{ marginBottom: 14 }}>
                    <Chip sentiment={tryIt.data.prediction.sentiment} /> <span className="muted"> top probability {pct(tryIt.data.prediction.confidence)}</span>
                    {tryIt.data.prediction.review_needed && <span className="warn"> · review needed</span>}
                  </p>
                  <ProbabilityBars p={{ positive: tryIt.data.prediction.prob_positive, neutral: tryIt.data.prediction.prob_neutral, negative: tryIt.data.prediction.prob_negative }} />
                </>
              ) : <Empty title="Write a comment and classify it">The three class probabilities appear here.</Empty>}
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="07" title="The training data">
            {r.dataset.name}, {r.dataset.license}. {r.dataset.label_mapping}.
          </SectionHead>
          <div className="figures" data-reveal>
            <div className="figure"><div className="label">Raw rows</div><div className="v num-figure">{clean.raw_rows}</div><div className="n">encoding {clean.encoding_detected}</div></div>
            <div className="figure"><div className="label">Duplicates removed</div><div className="v num-figure">{clean.dropped_duplicate_rows}</div></div>
            <div className="figure"><div className="label">Conflicting labels removed</div><div className="v num-figure">{clean.dropped_conflicting_rows}</div></div>
            <div className="figure"><div className="label">Clean labelled rows</div><div className="v num-figure">{clean.clean_rows}</div><div className="n">{r.split.train_rows} train / {r.split.test_rows} test</div></div>
          </div>
          <p className="small muted" style={{ marginTop: 18 }}>
            Source <a href={r.dataset.url} target="_blank" rel="noreferrer">{r.dataset.url}</a>. The synthetic demonstration dataset is never used for training or evaluation.
            Versions: Python {r.versions.python}, scikit-learn {r.versions.scikit_learn}, spaCy {r.versions.spacy} ({r.versions.spacy_model}).
          </p>
        </div>
      </section>
    </div>
  )
}
