const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options) {
  const response = await fetch(`${BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Request failed')
  return response.json()
}

export const api = {
  dashboard: () => request('/api/dashboard'),
  exceptions: () => request('/api/exceptions'),
  updateException: (id, status) => request(`/api/exceptions/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  filings: () => request('/api/filings'),
  approveFiling: (id) => request(`/api/filings/${id}/approve`, { method: 'POST' }),
  documents: () => request('/api/documents'),
  uploadDocument: (file, category) => request('/api/documents', { method: 'POST', body: JSON.stringify({ name: file.name, category }) }),
  tasks: () => request('/api/ca-tasks'),
  createTask: (title, assignee) => request('/api/ca-tasks', { method: 'POST', body: JSON.stringify({ title, assignee }) }),
  updateTask: (id, status) => request(`/api/ca-tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
}

