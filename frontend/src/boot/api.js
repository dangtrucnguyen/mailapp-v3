import axios from 'axios'
import { useAuthStore } from '../stores/auth'

// Detect Tauri vs browser
const isTauri = !!(window.__TAURI_INTERNALS__)

// API base URL: relative for SPA (proxied), absolute for Tauri
const baseURL = isTauri
  ? (localStorage.getItem('mailapp_api_url') || 'https://op13.scigroup.fr') + '/api'
  : '/api'

const api = axios.create({
  baseURL,
  withCredentials: false,
  headers: { 'Content-Type': 'application/json' }
})

// Interceptor: attach token
api.interceptors.request.use(config => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// Interceptor: handle 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      window.location.href = isTauri ? '/' : '/login'
    }
    return Promise.reject(err)
  }
)

export default api
