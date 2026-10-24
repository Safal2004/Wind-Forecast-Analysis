import { useState } from 'react'
import { fetchAnalysis } from './api/analysis'
import { ErrorChart, GenerationChart } from './components/Charts'
import KpiCards from './components/KpiCards'
import ResultsTable from './components/ResultsTable'

const initialFilters = { publishFrom: '', publishTo: '', settlementDate: '', cutoff: '' }

export default function App() {
  const [filters, setFilters] = useState(initialFilters)
  const [analysis, setAnalysis] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setError('')
    if (Object.values(filters).some((value) => !value)) {
      setError('Complete all filters before running the analysis.')
      return
    }
    setStatus('loading')
    try {
      const result = await fetchAnalysis(filters)
      setAnalysis(result)
      setStatus('success')
    } catch (requestError) {
      setError(requestError.message)
      setStatus('error')
    }
  }

  const periods = analysis?.periods || []
  return <main className="app-shell">
    <header><p className="eyebrow">Wind generation</p><h1>Forecast analysis</h1><p>Compare forecast versions selected at your purchasing decision cutoff with actual generation.</p></header>
    <section className="panel filters"><h2>Analysis filters</h2><form onSubmit={submit}>
      <label>Forecast publication from<input type="datetime-local" value={filters.publishFrom} onChange={(event) => setFilters({ ...filters, publishFrom: event.target.value })} required /></label>
      <label>Forecast publication to<input type="datetime-local" value={filters.publishTo} onChange={(event) => setFilters({ ...filters, publishTo: event.target.value })} required /></label>
      <label>Actuals settlement date<input type="date" value={filters.settlementDate} onChange={(event) => setFilters({ ...filters, settlementDate: event.target.value })} required /></label>
      <label>Purchasing decision cutoff<input type="datetime-local" value={filters.cutoff} onChange={(event) => setFilters({ ...filters, cutoff: event.target.value })} required /></label>
      <button disabled={status === 'loading'}>{status === 'loading' ? 'Running analysis…' : 'Run analysis'}</button>
    </form><p className="filter-note">Times are entered in your browser’s local timezone and sent to the backend as UTC timestamps.</p></section>
    {error && <section className="notice error" role="alert">{error}</section>}
    {!analysis && status !== 'loading' && !error && <section className="notice">Choose a publication window, settlement date, and cutoff to request real backend data.</section>}
    {status === 'loading' && <section className="notice" aria-live="polite">Retrieving and analysing data…</section>}
    {analysis && <>
      <KpiCards analysis={analysis} />
      <section className="charts"><GenerationChart periods={periods} /><ErrorChart periods={periods} /></section>
      <ResultsTable periods={periods} />
    </>}
  </main>
}
