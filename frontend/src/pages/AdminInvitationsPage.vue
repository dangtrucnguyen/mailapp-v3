<template>
  <div>
    <div class="text-h5 q-mb-md">📨 Invitations</div>
    <div class="q-mb-md">
      <q-form @submit="invite">
        <div class="row q-col-gutter-sm items-end">
          <div class="col-12 col-sm-4"><q-input v-model="form.email" label="Email" type="email" outlined dense :rules="[v => !!v]" /></div>
          <div class="col-12 col-sm-3"><q-select v-model="form.role" :options="['utilisateur','manager','admin']" label="Rôle" outlined dense /></div>
          <div class="col-12 col-sm-3"><q-select v-model="form.project_code" :options="projectOptions" label="Projet (optionnel)" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-sm-2"><q-btn type="submit" color="primary" label="Inviter" class="full-width" :loading="loading" /></div>
        </div>
      </q-form>
    </div>

    <q-table :rows="invitations" :columns="columns" row-key="id" flat bordered dense>
      <template v-slot:body-cell-is_used="props">
        <q-td><q-badge :color="props.value ? 'positive' : 'warning'">{{ props.value ? 'Acceptée' : 'En attente' }}</q-badge></q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const invitations = ref([])
const loading = ref(false)
const projectOptions = ref([])
const form = reactive({ email: '', role: 'utilisateur', project_code: '' })

const columns = [
  { name: 'email', label: 'Email', field: 'email', sortable: true },
  { name: 'role', label: 'Rôle', field: 'role' },
  { name: 'is_used', label: 'Statut', field: 'is_used' },
  { name: 'created_at', label: 'Date', field: 'created_at' }
]

onMounted(async () => {
  try { invitations.value = (await api.get('/admin/invitations')).data.invitations || [] } catch {}
  try { projectOptions.value = (await api.get('/projects?format=json')).data.projects?.map(p => ({ label: p.name, value: p.code })) || [] } catch {}
})

async function invite() {
  loading.value = true
  try {
    await api.post('/admin/api/users/invite', form)
    $q.notify({ type: 'positive', message: 'Invitation envoyée' })
    form.email = ''
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erreur' })
  } finally {
    loading.value = false
  }
}
</script>
