import axios from 'axios'

// Detect Tauri vs browser
const isTauri = !!(window.__TAURI_INTERNALS__)

// API base URL: relative for SPA (proxied), absolute for Tauri
const baseURL = isTauri
  ? (localStorage.getItem('mailapp_api_url') || 'http://192.168.1.242:6000') + '/api'
  : '/api'

const api = axios.create({
  baseURL,
  withCredentials: false,
  headers: { 'Content-Type': 'application/json' }
})

// Interceptor: attach token from localStorage (avoids circular dep with auth store)
api.interceptors.request.use(config => {
  const token = localStorage.getItem('mailapp_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor: handle 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('mailapp_token')
      window.location.href = isTauri ? '/' : '/login'
    }
    return Promise.reject(err)
  }
)

export default api
