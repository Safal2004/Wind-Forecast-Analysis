const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function metric(value) {
  return value === null || value === undefined ? '—' : number.format(value)
}

export default function KpiCards({ analysis }) {
  const cards = [
    ['MAE', metric(analysis.mae), 'Mean absolute error'],
    ['RMSE', metric(analysis.rmse), 'Root mean squared error'],
    ['Mean bias', metric(analysis.meanForecastBias), 'Forecast minus actual'],
    ['Matched intervals', number.format(analysis.matchedIntervalCount), 'Unambiguous matched periods'],
  ]

  return <section className="kpis" aria-label="Analysis metrics">
    {cards.map(([label, value, hint]) => <article className="kpi" key={label}>
      <span>{label}</span><strong>{value}</strong><small>{hint}</small>
    </article>)}
  </section>
}
