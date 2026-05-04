<template>
  <div>
    <div class="text-h5 q-mb-md">💾 Brouillons</div>
    <q-list separator>
      <q-item v-for="d in drafts" :key="d.id" clickable @click="$router.push(`/compose?draft=${d.id}`)">
        <q-item-section>
          <q-item-label>{{ d.subject || '(sans sujet)' }}</q-item-label>
          <q-item-label caption>{{ d.recipients || 'pas de destinataire' }} · {{ d.date_time?.substring(0, 16) }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-btn flat round icon="delete" @click.stop="deleteDraft(d.id)" size="sm" color="negative" />
        </q-item-section>
      </q-item>
    </q-list>
    <div v-if="!drafts.length" class="text-center q-pa-xl text-grey">
      <q-icon name="drafts" size="48px" /><p>Aucun brouillon</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const drafts = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/emails', { params: { mailbox: 'drafts', limit: 100 } })
    drafts.value = res.data.emails || []
  } catch (e) {
    console.error('DraftsPage:', e)
  }
})

async function deleteDraft(id) {
  try {
    await api.delete(`/emails/drafts/${id}`)
    drafts.value = drafts.value.filter(d => d.id !== id)
    $q.notify({ type: 'positive', message: 'Brouillon supprimé' })
  } catch {}
}
</script>
