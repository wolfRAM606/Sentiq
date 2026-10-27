import { useQuery } from '@tanstack/react-query'
import { SectionHead } from '../components/ui'
import { api } from '../lib/api'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

const STEPS: [string, string][] = [
  ['Ingestion and validation', 'CSV bytes are decoded (UTF-8, UTF-8 with BOM, Windows-1252, Latin-1) and the delimiter is detected. Every column is read as text so the original review is preserved, and columns are mapped to roles. Empty, non-alphabetic and duplicate reviews are excluded with a stated reason; unparseable dates and ratings are counted.'],
  ['spaCy preprocessing', 'en_core_web_sm tokenises, lemmatises, tags and parses each review. Generic stopwords are removed but negators, contrast words and intensifiers are kept. Up to three content words after a negator get a neg_ prefix, so "not helpful" becomes "not neg_helpful".'],
  ['Sentiment classification', 'A scikit-learn Pipeline (spaCy normaliser, TF-IDF of word n-grams, Logistic Regression with balanced class weights) trained on a verified public labelled dataset and compared with majority, Naive Bayes and linear SVM baselines. Hyper-parameters come from five-fold cross-validation on the training split; the stratified 20% test split is scored once.'],
  ['Uncertainty', 'Each prediction carries three class probabilities. Predictions with a top probability under 55%, or within 15 points of the runner-up, are flagged for human review. Calibration on the test set is reported on the Model page.'],
  ['Aspect analysis', 'Sentences are split into clauses at contrastive conjunctions and matched on lemmas against a configurable twelve-aspect lexicon with phrases, context-dependent words and exclusions. The classifier then scores the clause that triggered each match. This is rule-assisted, so no aspect-level accuracy is claimed.'],
  ['Keywords and topics', 'Lemma n-grams and spaCy noun chunks are counted once per review and split by predicted sentiment. Topics come from TF-IDF and non-negative matrix factorisation, skipped when the selection is too small or uniform.'],
  ['Insights and recommendations', 'Fixed rules with minimum-evidence thresholds. Each statement carries its counts, example clauses with record numbers, and caveats.'],
]

const LIMITS = [
  'Predictions are imperfect (about 65% accuracy on held-out data) and weakest for neutral comments.',
  'The training data comes from one institution, so the model may transfer poorly to other populations or disciplines.',
  'The aspect lexicon can miss paraphrases, sarcasm and domain-specific vocabulary.',
  'Student feedback can be biased (who chooses to respond, grade expectations), so indicators describe expressed opinion rather than teaching quality.',
  'All analyses are descriptive and do not support causal claims.',
  'Intended use: reflective, exploratory support for instructors and departments. It is not designed for automated evaluation, ranking or personnel decisions.',
]

export default function Method() {
  const { datasetId, filters } = useApp()
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const model = useQuery({ queryKey: ['model'], queryFn: api.model, staleTime: Infinity })
  const ref = useReveal<HTMLDivElement>()
  const m = meta.data
  const downloads: [string, string, string][] = [
    ['reviews.csv', 'Analysed reviews', 'CSV with original text, predictions, probabilities, aspects and processed text'],
    ['report.html', 'Printable report', 'HTML; use your browser\'s Print to save it as PDF'],
    ['report.md', 'Markdown report', 'The same report as plain Markdown'],
    ['mentions.csv', 'Aspect mentions', 'One row per review and aspect, with the evidence clause'],
    ['excluded.csv', 'Excluded records', 'Every record that was not analysed, with its reason'],
  ]
  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap">
          <div className="eyebrow" data-reveal>Method</div>
          <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
            Show your <em>working.</em>
          </h1>
          <p className="lede" style={{ marginTop: 22 }} data-reveal>How Sentiq turns raw comments into evidence, what it cannot do, where the data came from, and the files you can take away.</p>
          <div style={{ marginTop: 34, borderTop: '1px solid var(--rule)', paddingTop: 18 }} data-reveal>
            <div className="label">Academic project title</div>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(22px, 2.6vw, 32px)', marginTop: 8, maxWidth: '40ch' }} data-testid="academic-title">
              {m?.academic_title ?? 'An Automated Text Mining Dashboard for Evaluating Course Feedback and Teaching Effectiveness Reviews using spaCy and Streamlit'}
            </p>
            <p className="muted" style={{ marginTop: 8 }}>Product: Sentiq · NLP-Powered Course Feedback Intelligence. Every response tells a story.</p>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <SectionHead num="01" title="Take the analysis with you">Every download follows the current dataset and filters.</SectionHead>
          <div className="rows" data-testid="downloads">
            {downloads.map(([kind, title, note], i) => (
              <div className="row" key={kind} data-reveal>
                <div className="idx">{String(i + 1).padStart(2, '0')}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'baseline' }}>
                  <div><strong style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 22 }}>{title}</strong><p className="small muted">{note}</p></div>
                  <a className="btn ghost" href={api.exportUrl(datasetId, kind, filters)} download data-testid={`dl-${kind}`}>Download {kind.split('.').pop()?.toUpperCase()}</a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="02" title="The pipeline">Seven stages, the same for the demonstration data, uploads and single comments.</SectionHead>
          <div className="rows">
            {STEPS.map(([t, d], i) => (
              <div className="row" key={t} data-reveal>
                <div className="idx">{String(i + 1).padStart(2, '0')}</div>
                <div><strong style={{ fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 22 }}>{t}</strong><p className="muted" style={{ marginTop: 6, maxWidth: '82ch' }}>{d}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="03" title="Scales">Two summary numbers appear throughout.</SectionHead>
          <div className="split">
            <div data-reveal><div className="label">Average sentiment score</div><p className="quote" style={{ marginTop: 8 }}>mean of P(positive) − P(negative), from −1 to +1</p></div>
            <div data-reveal><div className="label">Feedback indicator</div><p className="quote" style={{ marginTop: 8 }}>100 × (positive share + ½ neutral share) = 50% positive share + 50% (1 − negative share)</p></div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="04" title="Limitations and appropriate use" />
          <div className="rows">
            {LIMITS.map((l, i) => (
              <div className="row" key={i} data-reveal><div className="idx">{String(i + 1).padStart(2, '0')}</div><div className="body" style={{ fontSize: 17 }}>{l}</div></div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <SectionHead num="05" title="Sources and versions" />
          <div className="split">
            <div className="stack" data-reveal>
              <p><strong>Sentiment training data.</strong> {model.data ? <>{model.data.dataset.name}, <a href={model.data.dataset.url} target="_blank" rel="noreferrer">{model.data.dataset.url}</a>, licence {model.data.dataset.license}. {model.data.dataset.cleaning.raw_rows} raw labelled comments, verified; {model.data.dataset.cleaning.clean_rows} after cleaning.</> : 'Loading.'}</p>
              <p><strong>Demonstration data.</strong> Synthetic, written for this project; not real student feedback and never used for training or evaluation.</p>
              <p><strong>EduRABSA</strong> (aspect-annotated education reviews, CC BY-NC-SA 4.0) was reviewed but not integrated: its data is distributed separately and its annotation scheme could not be mapped and validated reliably in the project timeline.</p>
              <p><strong>Uploads</strong> are processed in memory and never written to disk or logs.</p>
            </div>
            <div data-reveal>
              <table className="table">
                <tbody>
                  {Object.entries(m?.versions ?? {}).map(([k, v]) => <tr key={k}><td>{k.replace('_', ' ')}</td><td className="num mono">{v ?? 'n/a'}</td></tr>)}
                  <tr><td>sentiment model</td><td className="num mono">{m ? `${m.model.source}, trained ${m.model.trained_at}` : ''}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
