<template>
  <div>
    <div class="text-h5 q-mb-md">📤 Messages envoyés</div>
    <q-list separator>
      <q-item v-for="s in sent" :key="s.id">
        <q-item-section>
          <q-item-label>{{ s.subject }}</q-item-label>
          <q-item-label caption>{{ s.to_email }} · {{ s.sent_at?.substring(0, 16) }}</q-item-label>
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
onMounted(async () => { try { sent.value = (await api.get('/emails/sent/list')).data.sent_emails || [] } catch {} })
const sent = ref([])
</script>
