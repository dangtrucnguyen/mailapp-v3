import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../boot/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('mailapp_token') || '')
  const loading = ref(false)

  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) {
    loading.value = true
    try {
      const res = await api.post('/auth/login', { username, password })
      token.value = res.data.access_token
      user.value = res.data.user
      localStorage.setItem('mailapp_token', token.value)
      return { ok: true }
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'Erreur de connexion'
      return { ok: false, error: detail }
    } finally {
      loading.value = false
    }
  }

  async function register(data) {
    loading.value = true
    try {
      const res = await api.post('/auth/register', data)
      return { ok: true, data: res.data }
    } catch (e) {
      return { ok: false, error: e.response?.data?.detail || 'Erreur inscription' }
    } finally {
      loading.value = false
    }
  }

  async function checkAuth() {
    if (!token.value) return
    try {
      const res = await api.get('/auth/me')
      user.value = res.data.user
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = ''
    localStorage.removeItem('mailapp_token')
  }

  return { user, token, loading, isAdmin, login, register, checkAuth, logout }
})
