<template>
  <div class="column items-center justify-center" style="min-height:80vh">
    <q-card style="width:100%;max-width:400px">
      <q-card-section>
        <div class="text-h5 text-center q-mb-md">📧 MailApp V3</div>
        <q-form @submit="onSubmit">
          <q-input v-model="serverUrl" label="Adresse du serveur" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis']" autofocus
                   hint="http://192.168.1.242:6000" />
          <q-input v-model="username" label="Nom d'utilisateur" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis']" />
          <q-input v-model="password" label="Mot de passe" type="password" outlined dense class="q-mb-md"
                   :rules="[v => !!v || 'Requis']" />
          <q-btn type="submit" color="primary" label="Connexion" :loading="auth.loading" class="full-width" />
        </q-form>
        <div v-if="error" class="text-negative text-center q-mt-sm">{{ error }}</div>
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

const auth = useAuthStore()
const router = useRouter()
const serverUrl = ref(localStorage.getItem('mailapp_api_url') || '')
const username = ref('')
const password = ref('')
const error = ref('')

async function onSubmit() {
  // Store server URL + update axios base
  const url = serverUrl.value.replace(/\/+$/, '')
  localStorage.setItem('mailapp_api_url', url)
  api.defaults.baseURL = url + '/api'

  const r = await auth.login(username.value, password.value)
  if (r.ok) router.push('/')
  else error.value = r.error
}
</script>
