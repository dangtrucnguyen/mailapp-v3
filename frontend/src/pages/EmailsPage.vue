<template>
  <div>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h5">Emails</div>
      <q-btn color="primary" icon="edit" label="Nouveau message" @click="$router.push('/compose')" />
    </div>

    <q-list separator>
      <q-item v-for="e in emails" :key="e.id" clickable @click="$router.push(`/emails/${e.id}`)">
        <q-item-section avatar>
          <q-icon name="email" :color="e.project_code ? 'primary' : 'grey'" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ e.subject }}</q-item-label>
          <q-item-label caption>{{ e.sender?.substring(0, 50) }} · {{ e.date_time?.substring(0, 16) }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-badge v-if="e.project_name" color="blue-1" text-color="blue-8">{{ e.project_name?.substring(0, 15) }}</q-badge>
        </q-item-section>
      </q-item>
    </q-list>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../boot/api'

const emails = ref([])
onMounted(async () => {
  try {
    const res = await api.get('/emails?mailbox=inbox')
    emails.value = res.data.emails || res.data || []
  } catch {}
})
</script>
