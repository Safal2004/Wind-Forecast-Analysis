// Empty uses Nginx's same-origin /api/ proxy in the production container.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function fetchAnalysis(filters) {
  const query = new URLSearchParams({
    publish_datetime_from: toIso(filters.publishFrom),
    publish_datetime_to: toIso(filters.publishTo),
    settlement_date_from: filters.settlementDate,
    purchasing_decision_cutoff: toIso(filters.cutoff),
  })
  const response = await fetch(`${API_BASE_URL}/api/periods?${query}`)

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Analysis request failed (${response.status})`)
  }
  return response.json()
}

function toIso(value) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) throw new Error('Enter a valid local date and time.')
  return date.toISOString()
}
