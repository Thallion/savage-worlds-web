const BASE_URL = '/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(response.status, data.detail || 'Fehler bei der Anfrage')
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

// Multipart-Upload: Content-Type (mit Boundary) setzt der Browser selbst
async function requestForm<T>(path: string, method: string, form: FormData): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { method, headers, body: form })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const meldung =
      response.status === 413 ? 'Datei zu groß' : data.detail || 'Fehler bei der Anfrage'
    throw new ApiError(response.status, typeof meldung === 'string' ? meldung : 'Ungültige Eingabe')
  }

  return response.json()
}

async function requestBlob(path: string, body: unknown): Promise<Blob> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(response.status, data.detail || 'Fehler bei der Anfrage')
  }

  return response.blob()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  postBlob: (path: string, body: unknown) => requestBlob(path, body),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  putForm: <T>(path: string, form: FormData) => requestForm<T>(path, 'PUT', form),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T = void>(path: string, body?: unknown) =>
    request<T>(path, { method: 'DELETE', ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }),
}

export { ApiError }
