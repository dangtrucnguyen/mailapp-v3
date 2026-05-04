<template>
  <div>
    <q-breadcrumbs class="q-mb-md">
      <q-breadcrumbs-el label="Projets" to="/projects" />
      <q-breadcrumbs-el :label="project?.code" />
    </q-breadcrumbs>

    <div v-if="project" class="text-h5 q-mb-xs">{{ project.name }}</div>
    <div class="text-caption text-grey q-mb-md">{{ project.code }} · {{ project.status }}</div>

    <q-tabs v-model="tab" dense class="q-mb-md" indicator-color="primary" active-color="primary">
      <q-tab name="team" icon="people" label="Équipe" />
      <q-tab name="tasks" icon="assignment" label="Tâches" />
      <q-tab name="emails" icon="email" label="Emails" />
      <q-tab name="docs" icon="description" label="Documents" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <!-- Équipe -->
      <q-tab-panel name="team">
        <q-list separator>
          <q-item v-for="m in members" :key="m.user_id">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" size="sm">{{ m.display_name?.[0] || m.username?.[0] }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.display_name || m.username }}
                <q-badge v-if="m.user_id === auth.user?.id" color="grey" outline>vous</q-badge>
              </q-item-label>
              <q-item-label caption>{{ m.email }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="m.role === 'chef' ? 'primary' : m.role === 'collaborateur' ? 'info' : 'grey'">{{ m.role }}</q-badge>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- Tâches -->
      <q-tab-panel name="tasks">
        <q-table :rows="tasks" :columns="taskCols" row-key="id" flat bordered dense
                 @row-click="(evt, row) => $router.push('/tasks')">
          <template v-slot:body-cell-status="props">
            <q-td><q-badge>{{ props.value }}</q-badge></q-td>
          </template>
        </q-table>
      </q-tab-panel>

      <!-- Emails -->
      <q-tab-panel name="emails">
        <q-list separator>
          <q-item v-for="e in emails" :key="e.id" clickable @click="$router.push(`/emails/${e.id}`)">
            <q-item-section>
              <q-item-label>{{ e.subject }}</q-item-label>
              <q-item-label caption>{{ e.sender?.substring(0, 40) }} · {{ e.date_time?.substring(0, 16) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>

      <!-- Documents -->
      <q-tab-panel name="docs">
        <div class="q-mb-md">
          <q-uploader :url="`/documents/api/upload`" label="Ajouter un document" auto-upload
                      field-name="file" :form-fields="[{ name: 'project_code', value: code }]" />
        </div>
        <q-list separator>
          <q-item v-for="d in docs" :key="d.id">
            <q-item-section avatar><q-icon name="insert_drive_file" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ d.filename }} <q-badge outline>v{{ d.version }}</q-badge></q-item-label>
              <q-item-label caption>{{ d.author_name }} · {{ d.created_at?.substring(0, 10) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat round icon="download" @click="downloadDoc(d.id)" size="sm" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../boot/api'

const route = useRoute()
const auth = useAuthStore()
const code = route.params.code

const tab = ref('team')
const project = ref(null)
const members = ref([])
const tasks = ref([])
const emails = ref([])
const docs = ref([])

const taskCols = [
  { name: 'code', label: 'Code', field: 'code', sortable: true },
  { name: 'title', label: 'Titre', field: 'title' },
  { name: 'status', label: 'Statut', field: 'status' },
  { name: 'priority', label: 'Priorité', field: 'priority' },
  { name: 'assignee_name', label: 'Assigné', field: 'assignee_name' }
]

async function loadProject() {
  try {
    // Récupérer les données depuis les routes API
    const [p, t, e, d] = await Promise.allSettled([
      api.get(`/projects/${code}`),
      api.get(`/tasks?project=${code}`),
      api.get(`/emails?project=${code}`),
      api.get(`/documents?project=${code}`)
    ])
    if (p.status === 'fulfilled') {
      project.value = p.value.data.project
      members.value = p.value.data.members || []
    }
    if (t.status === 'fulfilled') tasks.value = t.value.data.tasks || t.value.data || []
    if (e.status === 'fulfilled') emails.value = e.value.data.emails || e.value.data || []
    if (d.status === 'fulfilled') docs.value = d.value.data.documents || d.value.data || []
  } catch {}
}

function downloadDoc(id) {
  window.open(`/documents/file/${id}`, '_blank')
}

onMounted(loadProject)
</script>
