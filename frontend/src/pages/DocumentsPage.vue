<template>
  <div>
    <div class="text-h5 q-mb-md">📄 Documents</div>
    <q-table :rows="docs" :columns="columns" row-key="id" flat bordered dense>
      <template v-slot:body-cell-actions="props">
        <q-td>
          <q-btn flat round icon="download" @click="download(props.row.id)" size="sm" />
          <q-btn flat round icon="delete" @click="remove(props.row.id)" size="sm" color="negative" />
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const docs = ref([])
const columns = [
  { name: 'filename', label: 'Fichier', field: 'filename', sortable: true },
  { name: 'description', label: 'Description', field: 'description' },
  { name: 'version', label: 'Version', field: 'version' },
  { name: 'status', label: 'Statut', field: 'status' },
  { name: 'created_at', label: 'Date', field: 'created_at' },
  { name: 'actions', label: '', field: 'id' }
]

onMounted(async () => {
  try { docs.value = (await api.get('/documents/api?format=json')).data.documents || [] } catch {}
})

function download(id) { window.open(`/documents/file/${id}`, '_blank') }

async function remove(id) {
  $q.dialog({ title: 'Supprimer', message: 'Supprimer ce document ?', ok: 'Oui', cancel: 'Non' })
    .onOk(async () => {
      await api.post(`/documents/api/${id}/delete`)
      docs.value = docs.value.filter(d => d.id !== id)
      $q.notify({ type: 'positive', message: 'Document supprimé' })
    })
}
</script>
