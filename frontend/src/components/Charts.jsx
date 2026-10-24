function plotPoints(values, min, max) {
  const span = max - min || 1
  return values.map((value, index) => {
    const x = values.length === 1 ? 50 : (index / (values.length - 1)) * 100
    const y = 88 - ((value - min) / span) * 76
    return `${x},${y}`
  }).join(' ')
}

function ChartFrame({ title, children, legend }) {
  return <article className="panel chart-panel">
    <div className="panel-heading"><h2>{title}</h2>{legend && <div className="legend">{legend}</div>}</div>
    {children}
  </article>
}

export function GenerationChart({ periods }) {
  if (!periods.length) return <ChartFrame title="Forecast vs actual"><EmptyChart /></ChartFrame>
  const forecast = periods.map((period) => period.forecastGeneration)
  const actual = periods.map((period) => period.actualGeneration)
  const min = Math.min(...forecast, ...actual)
  const max = Math.max(...forecast, ...actual)
  return <ChartFrame title="Forecast vs actual" legend={<><i className="forecast" /> Forecast <i className="actual" /> Actual</>}>
    <svg className="chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Forecast and actual generation by delivery interval">
      <line x1="0" x2="100" y1="88" y2="88" className="grid" />
      <polyline points={plotPoints(forecast, min, max)} className="forecast-line" />
      <polyline points={plotPoints(actual, min, max)} className="actual-line" />
    </svg>
  </ChartFrame>
}

export function ErrorChart({ periods }) {
  if (!periods.length) return <ChartFrame title="Forecast error"><EmptyChart /></ChartFrame>
  const errors = periods.map((period) => period.forecastGeneration - period.actualGeneration)
  const bound = Math.max(...errors.map(Math.abs)) || 1
  return <ChartFrame title="Forecast error" legend="Forecast − actual">
    <svg className="chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Forecast error by delivery interval">
      <line x1="0" x2="100" y1="50" y2="50" className="grid" />
      {errors.map((error, index) => {
        const width = Math.max(2, 86 / errors.length)
        const x = 7 + index * (86 / errors.length)
        const height = (Math.abs(error) / bound) * 37
        const y = error >= 0 ? 50 - height : 50
        return <rect className={error >= 0 ? 'positive-bar' : 'negative-bar'} key={`${index}-${error}`} x={x} y={y} width={width} height={height} />
      })}
    </svg>
  </ChartFrame>
}

function EmptyChart() {
  return <div className="empty-chart">No matched delivery periods to plot.</div>
}
