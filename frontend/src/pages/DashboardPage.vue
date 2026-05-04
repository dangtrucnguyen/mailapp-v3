<template>
  <div>
    <div class="text-h5 q-mb-md">Dashboard</div>
    <p class="text-grey">Bienvenue, {{ auth.user?.display_name || auth.user?.username }}</p>

    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-6 col-sm-3">
        <q-card flat bordered class="text-center q-pa-md">
          <div class="text-h4 text-primary">{{ stats.projects }}</div>
          <div class="text-caption text-grey">{{ auth.isAdmin ? 'Projets total' : 'Mes projets' }}</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3" v-if="auth.isAdmin">
        <q-card flat bordered class="text-center q-pa-md">
          <div class="text-h4 text-primary">{{ stats.users }}</div>
          <div class="text-caption text-grey">Utilisateurs</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3">
        <q-card flat bordered class="text-center q-pa-md">
          <div class="text-h4 text-info">{{ stats.emails }}</div>
          <div class="text-caption text-grey">Emails</div>
        </q-card>
      </div>
      <div class="col-6 col-sm-3">
        <q-card flat bordered class="text-center q-pa-md">
          <div class="text-h4 text-accent">{{ stats.tasks }}</div>
          <div class="text-caption text-grey">Tâches</div>
        </q-card>
      </div>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1">Derniers emails</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="e in recentEmails" :key="e.id" clickable @click="$router.push(`/emails/${e.id}`)">
          <q-item-section avatar><q-icon name="email" :color="e.project_code ? 'primary' : 'grey'" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ e.subject }}</q-item-label>
            <q-item-label caption>{{ e.sender?.substring(0, 50) }} · {{ e.date_time?.substring(0, 16) }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../boot/api'

const auth = useAuthStore()
const stats = ref({ projects: 0, users: 0, emails: 0, tasks: 0 })
const recentEmails = ref([])

onMounted(async () => {
  try {
    // Récupérer stats depuis l'API
    const [pres, eres] = await Promise.allSettled([
      api.get('/projects'),
      api.get('/emails')
    ])
    if (pres.status === 'fulfilled') {
      stats.value.projects = pres.value.data.length || 0
    }
    if (eres.status === 'fulfilled') {
      stats.value.emails = eres.value.data.emails?.length || eres.value.data.length || 0
      recentEmails.value = (eres.value.data.emails || eres.value.data || []).slice(0, 5)
    }
  } catch {}
})
</script>
