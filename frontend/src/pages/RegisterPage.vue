<template>
  <div class="column items-center justify-center" style="min-height:80vh">
    <q-card style="width:100%;max-width:400px">
      <q-card-section>
        <div class="text-h5 text-center q-mb-md">Créer un compte</div>
        <q-form @submit="onSubmit">
          <q-input v-model="form.username" label="Nom d'utilisateur" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis', v => v.length >= 3 || '3 caractères min']" />
          <q-input v-model="form.email" label="Email" type="email" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis']" />
          <q-input v-model="form.display_name" label="Nom complet" outlined dense class="q-mb-sm" />
          <q-input v-model="form.password" label="Mot de passe" type="password" outlined dense class="q-mb-md"
                   :rules="[v => !!v || 'Requis', v => v.length >= 6 || '6 caractères min']" />
          <q-btn type="submit" color="primary" label="S'inscrire" :loading="auth.loading" class="full-width" />
        </q-form>
        <div v-if="error" class="text-negative text-center q-mt-sm">{{ error }}</div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn flat to="/login" label="Déjà un compte ?" size="sm" />
      </q-card-actions>
    </q-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ username: '', email: '', display_name: '', password: '' })
const error = ref('')

async function onSubmit() {
  const r = await auth.register(form)
  if (r.ok) router.push('/login?registered=1')
  else error.value = r.error
}
</script>
