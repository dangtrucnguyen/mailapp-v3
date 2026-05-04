<template>
  <div>
    <div class="text-h5 q-mb-md">📤 Messages envoyés</div>

    <q-list separator>
      <q-item v-for="s in sent" :key="s.hash" clickable @click="$router.push(`/emails/${s.hash}`)">
        <q-item-section avatar>
          <q-icon name="send" :color="s.project_code ? 'primary' : 'grey'" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ s.subject }}</q-item-label>
          <q-item-label caption>À: {{ (s.recipients || '').substring(0, 50) }} · {{ s.date_time?.substring(0, 16) }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-badge v-if="s.project_name" color="blue-1" text-color="blue-8">{{ s.project_name?.substring(0, 15) }}</q-badge>
        </q-item-section>
      </q-item>
    </q-list>

    <div v-if="!sent.length" class="text-center q-pa-xl text-grey">
      <q-icon name="send" size="48px" /><p>Aucun message envoyé</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../boot/api'

const sent = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/emails', { params: { mailbox: 'sent', limit: 100 } })
    sent.value = res.data.emails || []
  } catch (e) {
    console.error('SentPage:', e)
  }
})
</script>
