const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

export default function ResultsTable({ periods }) {
  return <section className="panel table-panel">
    <div className="panel-heading"><h2>Delivery-period results</h2><span>{periods.length} rows</span></div>
    {!periods.length ? <p className="empty-table">No matched delivery periods returned for these filters.</p> : <div className="table-scroll"><table>
      <thead><tr><th>Delivery start</th><th>Forecast published</th><th>Forecast</th><th>Actual</th><th>Error</th></tr></thead>
      <tbody>{periods.map((period) => {
        const error = period.forecastGeneration - period.actualGeneration
        return <tr key={`${period.startTime}-${period.publishTime}`}>
          <td>{formatTime(period.startTime)}</td><td>{formatTime(period.publishTime)}</td>
          <td>{number.format(period.forecastGeneration)}</td><td>{number.format(period.actualGeneration)}</td>
          <td className={error >= 0 ? 'positive' : 'negative'}>{number.format(error)}</td>
        </tr>
      })}</tbody>
    </table></div>}
  </section>
}

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
