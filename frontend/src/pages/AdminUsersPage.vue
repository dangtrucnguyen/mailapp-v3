<template>
  <div>
    <div class="text-h5 q-mb-md">👥 Utilisateurs</div>
    <q-table :rows="users" :columns="columns" row-key="id" flat bordered dense>
      <template v-slot:body-cell-is_active="props">
        <q-td><q-badge :color="props.value ? 'positive' : 'negative'">{{ props.value ? 'Actif' : 'Désactivé' }}</q-badge></q-td>
      </template>
      <template v-slot:body-cell-role="props">
        <q-td><q-badge :color="props.value === 'admin' ? 'primary' : 'grey'">{{ props.value }}</q-badge></q-td>
      </template>
      <template v-slot:body-cell-actions="props">
        <q-td>
          <div class="q-gutter-xs">
            <q-btn flat round icon="toggle_on" size="sm" @click="toggleUser(props.row)"
                   :color="props.row.is_active ? 'warning' : 'positive'" :title="props.row.is_active ? 'Désactiver' : 'Activer'" />
            <q-btn flat round icon="manage_accounts" size="sm" @click="changeRole(props.row)" title="Changer rôle" />
          </div>
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
const users = ref([])
const columns = [
  { name: 'username', label: 'Utilisateur', field: 'username', sortable: true },
  { name: 'email', label: 'Email', field: 'email' },
  { name: 'role', label: 'Rôle', field: 'role' },
  { name: 'is_active', label: 'Statut', field: 'is_active' },
  { name: 'actions', label: 'Actions', field: 'id' }
]

onMounted(async () => {
  try {
    users.value = (await api.get('/admin/users')).data.users || []
  } catch {}
})

async function toggleUser(user) {
  try {
    await api.post(`/admin/users/${user.id}/toggle`)
    user.is_active = user.is_active ? 0 : 1
    $q.notify({ type: 'positive', message: user.is_active ? 'Utilisateur activé' : 'Utilisateur désactivé' })
  } catch {}
}

function changeRole(user) {
  const newRole = user.role === 'admin' ? 'manager' : user.role === 'manager' ? 'utilisateur' : 'admin'
  $q.dialog({
    title: 'Changer le rôle',
    message: `Passer ${user.username} de ${user.role} à ${newRole} ?`,
    ok: 'Confirmer', cancel: 'Annuler'
  }).onOk(async () => {
    await api.post(`/admin/users/${user.id}/role`, { role: newRole })
    user.role = newRole
    $q.notify({ type: 'positive', message: 'Rôle mis à jour' })
  })
}
</script>
