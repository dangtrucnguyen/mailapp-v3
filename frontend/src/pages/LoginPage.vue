<template>
  <div class="column items-center justify-center" style="min-height:80vh">
    <q-card style="width:100%;max-width:400px">
      <q-card-section>
        <div class="text-h5 text-center q-mb-md">📧 MailApp V3</div>
        <q-input v-if="isTauri" v-model="serverUrl" label="Adresse du serveur" outlined dense class="q-mb-sm"
                 autofocus hint="http://192.168.1.242:6000" />
        <q-input v-model="username" label="Nom d'utilisateur" outlined dense class="q-mb-sm" :autofocus="!isTauri" />
        <q-input v-model="password" label="Mot de passe" type="password" outlined dense class="q-mb-md"
                 @keyup.enter="onSubmit" />
        <q-btn color="primary" label="Connexion" :loading="auth.loading" class="full-width" @click="onSubmit" />
        <div v-if="error" class="text-negative text-center q-mt-sm">{{ error }}</div>
        <div v-if="debugInfo && isTauri" class="text-grey-6 text-center q-mt-xs" style="font-size:11px">{{ debugInfo }}</div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn flat to="/register" label="Créer un compte" size="sm" />
      </q-card-actions>
    </q-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../boot/api'

const isTauri = !!(window.__TAURI_INTERNALS__)

const auth = useAuthStore()
const router = useRouter()
const serverUrl = ref(localStorage.getItem('mailapp_api_url') || '')
const username = ref('')
const password = ref('')
const error = ref('')
const debugInfo = ref('')

async function onSubmit() {
  error.value = ''
  debugInfo.value = ''

  // Manual validation
  if (isTauri && !serverUrl.value.trim()) { error.value = 'Adresse du serveur requise'; return }
  if (!username.value.trim()) { error.value = 'Nom d\'utilisateur requis'; return }
  if (!password.value) { error.value = 'Mot de passe requis'; return }

  try {
    if (isTauri) {
      const url = serverUrl.value.trim().replace(/\/+$/, '')
      const apiBase = url + '/api'
      localStorage.setItem('mailapp_api_url', url)
      api.defaults.baseURL = apiBase
      debugInfo.value = 'Connexion à ' + apiBase + '...'
    } else {
      // Web: use relative /api path
      api.defaults.baseURL = '/api'
      localStorage.removeItem('mailapp_api_url')
    }

    const r = await auth.login(username.value, password.value)
    if (r.ok) {
      router.push('/')
    } else {
      error.value = r.error
    }
  } catch (e) {
    error.value = 'Erreur: ' + (e.message || String(e))
  }
}
</script>
