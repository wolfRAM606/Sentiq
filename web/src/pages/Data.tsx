import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Empty, ErrorNote, Loading, SectionHead } from '../components/ui'
import { api } from '../lib/api'
import { useReveal } from '../lib/motion'
import { useApp } from '../lib/store'

type UploadInfo = Awaited<ReturnType<typeof api.upload>>
const NONE = '(not available)'

export default function Data() {
  const { datasetId, setDataset } = useApp()
  const qc = useQueryClient()
  const meta = useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
  const validation = useQuery({ queryKey: ['validation', datasetId], queryFn: () => api.validation(datasetId) })
  const ds = useQuery({ queryKey: ['dataset', datasetId], queryFn: () => api.dataset(datasetId), retry: false })
  const [info, setInfo] = useState<UploadInfo | null>(null)
  const [mapping, setMapping] = useState<Record<string, string | null>>({})
  const [name, setName] = useState('')
  const [done, setDone] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const ref = useReveal<HTMLDivElement>([info, validation.data])

  const analyse = useMutation({
    mutationFn: () => api.analyzeUpload(info!.upload_id, mapping, name),
    onSuccess: (s) => {
      qc.invalidateQueries()
      setDataset(s.id)
      setDone(`Analysed ${s.report.valid_records} valid reviews from ${s.name}; ${s.report.excluded_records} record(s) excluded. Every page now shows this dataset.`)
      setInfo(null)
    },
  })

  const upload = useMutation({
    mutationFn: (f: File) => {
      const maxMb = meta.data?.limits.max_upload_mb ?? 10
      if (f.size > maxMb * 1024 * 1024) return Promise.reject(new Error(`The file is larger than the ${maxMb} MB limit.`))
      return api.upload(f)
    },
    onSuccess: (r) => {
      analyse.reset() // drop any error left over from analysing a previous file
      setInfo(r)
      setMapping(r.suggested_mapping)
      setName(r.filename)
      setDone(null)
    },
    onError: () => setInfo(null),
  })
  const roles = meta.data?.roles ?? []
  const used = Object.values(mapping).filter(Boolean) as string[]
  const duplicate = used.length !== new Set(used).size
  const pick = (f: File | undefined) => f && upload.mutate(f)
  const rep = validation.data?.report

  return (
    <div ref={ref}>
      <section className="hero" style={{ paddingBottom: 40 }}>
        <div className="wrap">
          <div className="eyebrow" data-reveal>Data</div>
          <h1 className="display" style={{ marginTop: 18, fontSize: 'clamp(42px, 6.4vw, 88px)' }} data-reveal>
            Bring your <em>own feedback.</em>
          </h1>
          <p className="lede" style={{ marginTop: 22 }} data-reveal>
            Upload a CSV with one review per row. Sentiq detects the encoding, delimiter and likely columns, shows you a preview, and
            accounts for every record: nothing is dropped without a reason. Files are processed in memory and never written to disk.
          </p>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 40 }}>
        <div className="wrap">
          <SectionHead num="01" title="Upload a CSV">
            Up to {meta.data?.limits.max_upload_mb ?? 10} MB and {(meta.data?.limits.max_rows ?? 10000).toLocaleString('en-GB')} rows. UTF-8,
            Windows-1252 and Latin-1 encodings, and comma, semicolon, tab or pipe delimiters are handled automatically.
          </SectionHead>
          <div
            data-reveal
            className="empty"
            style={{ borderStyle: dragging ? 'solid' : 'dashed', borderColor: dragging ? 'var(--brand)' : undefined, textAlign: 'center', padding: '44px 24px', cursor: 'pointer' }}
            onDragOver={(e) => (e.preventDefault(), setDragging(true))}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => (e.preventDefault(), setDragging(false), pick(e.dataTransfer.files[0]))}
            onClick={() => fileRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && fileRef.current?.click()}
          >
            <strong>Drop a CSV here, or choose a file</strong>
            <span>Review text is required; course, instructor, date, semester and rating are optional.</span>
            <input ref={fileRef} type="file" accept=".csv,.txt,text/csv" hidden data-testid="file-input" onChange={(e) => (pick(e.target.files?.[0]), (e.target.value = ''))} />
          </div>
          <div style={{ marginTop: 16 }}>
            {upload.isPending && <Loading what="Reading the file" />}
            {upload.error && <ErrorNote error={upload.error} />}
            {done && <p className="notice ok" role="status" data-testid="upload-done">{done}</p>}
          </div>
          {datasetId !== 'demo' && (
            <p style={{ marginTop: 16 }}>
              <button type="button" className="link-btn" onClick={() => (qc.invalidateQueries(), setDataset('demo'), setDone(null))} data-testid="reset-demo">
                Reset to the demonstration dataset
              </button>
            </p>
          )}
        </div>
      </section>

      {info && (
        <section className="section">
          <div className="wrap">
            <SectionHead num="02" title="Check the columns">
              Read {info.rows.toLocaleString('en-GB')} rows and {info.columns.length} columns (encoding {info.encoding}, delimiter "
              {info.delimiter === '\t' ? 'tab' : info.delimiter}"). Each column can be used for one role only.
            </SectionHead>
            {info.truncated && (
              <p className="notice demo" style={{ marginBottom: 18 }}>The file has {info.original_rows.toLocaleString('en-GB')} rows; only the first {info.rows.toLocaleString('en-GB')} will be analysed.</p>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 18 }} data-reveal>
              {roles.map((r) => (
                <label className="field" key={r.role}>
                  <span>{r.label}</span>
                  <select
                    className="select"
                    value={mapping[r.role] ?? NONE}
                    data-testid={`map-${r.role}`}
                    onChange={(e) => setMapping({ ...mapping, [r.role]: e.target.value === NONE ? null : e.target.value })}
                  >
                    {!r.required && <option value={NONE}>{NONE}</option>}
                    {info.columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
              ))}
              <label className="field">
                <span>Dataset name</span>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} data-testid="dataset-name-input" />
              </label>
            </div>
            {duplicate && <p className="notice error" style={{ marginTop: 16 }} role="alert">Each column can be mapped to only one role.</p>}
            <div className="label" style={{ margin: '34px 0 10px' }}>Preview, first {info.preview.length} rows</div>
            <div className="table-wrap" data-reveal>
              <table className="table">
                <thead><tr>{info.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {info.preview.map((row, i) => (
                    <tr key={i}>{info.columns.map((c) => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 26, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <button type="button" className="btn" disabled={duplicate || !mapping.text || analyse.isPending} onClick={() => analyse.mutate()} data-testid="analyse">
                {analyse.isPending ? 'Analysing' : 'Analyse dataset'}
              </button>
              <button type="button" className="btn ghost" onClick={() => setInfo(null)}>Cancel</button>
            </div>
            {analyse.isPending && <div style={{ marginTop: 14 }}><Loading what="Running spaCy, the classifier and aspect matching" /></div>}
            {analyse.error && <div style={{ marginTop: 14 }}><ErrorNote error={analyse.error} /></div>}
          </div>
        </section>
      )}

      <section className="section">
        <div className="wrap">
          <SectionHead num={info ? '03' : '02'} title="Validation report">
            For the active dataset{ds.data ? `, ${ds.data.name}` : ''}. Every record in the file is either analysed or listed here with the reason it was excluded.
          </SectionHead>
          {validation.isLoading && <Loading />}
          {validation.error && <ErrorNote error={validation.error} />}
          {rep && (
            <>
              <div className="figures" data-reveal>
                {[
                  ['Records in file', rep.total_records],
                  ['Valid reviews', rep.valid_records],
                  ['Excluded', rep.excluded_records],
                  ['Truncated long reviews', rep.truncated_reviews],
                ].map(([l, v]) => (
                  <div className="figure" key={l as string}>
                    <div className="label">{l}</div>
                    <div className="v num-figure" data-testid={`val-${l}`}>{v}</div>
                  </div>
                ))}
              </div>
              {rep.warnings.length > 0 && (
                <div className="stack" style={{ marginTop: 22 }}>
                  {rep.warnings.map((w) => <p className="notice demo" key={w}>{w}</p>)}
                </div>
              )}
              <div className="split" style={{ marginTop: 36 }}>
                <div data-reveal>
                  <div className="label" style={{ marginBottom: 10 }}>Column mapping used</div>
                  <table className="table">
                    <tbody>
                      {Object.entries(rep.mapped_columns).map(([role, col]) => (
                        <tr key={role}><td>{role}</td><td>{col ?? <span className="muted">not mapped</span>}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div data-reveal>
                  <div className="label" style={{ marginBottom: 10 }}>Excluded records</div>
                  {validation.data!.excluded.length ? (
                    <table className="table" data-testid="excluded-table">
                      <thead><tr><th>#</th><th>Text</th><th>Reason</th></tr></thead>
                      <tbody>
                        {validation.data!.excluded.map((r) => (
                          <tr key={r.record_id}>
                            <td className="mono">{r.record_id}</td>
                            <td>{r.review_text?.trim() ? r.review_text : <span className="muted">(empty)</span>}</td>
                            <td>{r.exclusion_reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <Empty title="No exclusions">Every record was analysed.</Empty>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
