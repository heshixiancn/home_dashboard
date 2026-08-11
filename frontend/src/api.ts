export type Health = {
  status: string
  http_status: number | null
  latency_ms: number | null
  error_message: string | null
  checked_at: string | null
}

export type Device = {
  id: number
  name: string
  host: string
  device_type: string
  icon: string
  description: string
  sort_order: number
  service_count: number
  online_count: number
  created_at: string
  updated_at: string
}

export type Service = {
  id: number
  device_id: number
  name: string
  protocol: 'http' | 'https'
  port: number | null
  path: string
  custom_url: string | null
  icon: string
  description: string
  favorite: boolean
  enabled: boolean
  health_enabled: boolean
  health_method: 'GET' | 'HEAD'
  timeout_ms: number
  sort_order: number
  url: string
  device_name: string
  device_host: string
  health: Health | null
  created_at: string
  updated_at: string
}

export type Dashboard = { devices: Device[]; services: Service[] }

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })
  if (!response.ok) {
    let message = response.statusText
    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {}
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  dashboard: () => request<Dashboard>('/api/dashboard'),
  createDevice: (payload: Partial<Device>) => request<Device>('/api/devices', { method: 'POST', body: JSON.stringify(payload) }),
  updateDevice: (id: number, payload: Partial<Device>) => request<Device>(`/api/devices/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteDevice: (id: number, cascade: boolean) => request<void>(`/api/devices/${id}?cascade=${cascade}`, { method: 'DELETE' }),
  createService: (payload: Partial<Service>) => request<Service>('/api/services', { method: 'POST', body: JSON.stringify(payload) }),
  updateService: (id: number, payload: Partial<Service>) => request<Service>(`/api/services/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteService: (id: number) => request<void>(`/api/services/${id}`, { method: 'DELETE' }),
  favorite: (id: number, favorite: boolean) => request<Service>(`/api/services/${id}/favorite`, { method: 'PATCH', body: JSON.stringify({ favorite }) }),
  check: (id: number) => request<Health>(`/api/services/${id}/check`, { method: 'POST' })
}

