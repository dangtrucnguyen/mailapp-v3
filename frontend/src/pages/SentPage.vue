<template>
  <div>
    <div class="text-h5 q-mb-md">📤 Messages envoyés</div>
    <q-list separator>
      <q-item v-for="s in sent" :key="s.id">
        <q-item-section>
          <q-item-label>{{ s.subject }}</q-item-label>
          <q-item-label caption>{{ s.recipients || s.sender }} · {{ s.date_time?.substring(0, 16) }}</q-item-label>
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
