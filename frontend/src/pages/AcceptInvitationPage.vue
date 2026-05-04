<template>
  <div class="column items-center justify-center" style="min-height:80vh">
    <q-card style="width:100%;max-width:400px">
      <q-card-section>
        <div class="text-h5 text-center q-mb-md">📨 Invitation</div>
        <q-form @submit="accept">
          <q-input v-model="form.username" label="Nom d'utilisateur" outlined dense class="q-mb-sm" :rules="[v => !!v]" />
          <q-input v-model="form.password" label="Mot de passe" type="password" outlined dense class="q-mb-sm"
                   :rules="[v => !!v && v.length >= 6 || '6 caractères min']" />
          <q-input v-model="form.display_name" label="Nom complet" outlined dense class="q-mb-md" />
          <q-btn type="submit" color="primary" label="Accepter l'invitation" :loading="loading" class="full-width" />
        </q-form>
        <div v-if="error" class="text-negative text-center q-mt-sm">{{ error }}</div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../boot/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '', display_name: '', token: route.query.token || '' })

async function accept() {
  loading.value = true
  try {
    const res = await api.post('/auth/register-with-invitation', form)
    auth.token = res.data.access_token
    auth.user = res.data.user
    localStorage.setItem('mailapp_token', auth.token)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur'
  } finally {
    loading.value = false
  }
}
</script>
