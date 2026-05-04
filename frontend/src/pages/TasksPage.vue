<template>
  <div>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h5">Tâches</div>
      <q-btn color="primary" icon="add" label="Nouvelle tâche" @click="openCreate" />
    </div>

    <!-- Desktop: Kanban columns -->
    <div class="row q-col-gutter-sm gt-sm">
      <div v-for="col in columns" :key="col" class="col-3">
        <q-card flat bordered>
          <q-card-section class="bg-grey-2">
            <div class="text-subtitle2">{{ col }}
              <q-badge color="grey" class="q-ml-sm">{{ tasks.filter(t => t.status === col).length }}</q-badge>
            </div>
          </q-card-section>
          <q-card-section class="q-pa-sm" style="min-height:200px"
                          @dragover.prevent @drop="onDrop($event, col)">
            <q-card v-for="t in tasks.filter(tsk => tsk.status === col)" :key="t.id"
                    flat bordered class="q-mb-sm" :class="'priority-' + (t.priority || 'normale').toLowerCase()"
                    draggable="true" @dragstart="onDragStart($event, t.id)"
                    @click="openEdit(t)" style="cursor:pointer">
              <q-card-section class="q-pa-sm">
                <div class="text-caption text-primary text-weight-bold">{{ t.code }}</div>
                <div class="text-body2">{{ t.title }}</div>
                <div class="text-caption text-grey q-mt-xs">
                  <span v-if="t.project_name">📁 {{ t.project_name }}</span>
                  <span v-if="t.assignee_name" class="q-ml-sm">👤 {{ t.assignee_name }}</span>
                  <span v-if="t.due_date" class="q-ml-sm">📅 {{ t.due_date?.substring(0, 10) }}</span>
                </div>
              </q-card-section>
            </q-card>
            <div v-if="!tasks.filter(t => t.status === col).length" class="text-center text-grey q-pa-md">
              —
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Mobile: tabs -->
    <div class="lt-md">
      <q-tabs v-model="mobileCol" dense class="q-mb-md">
        <q-tab v-for="col in columns" :key="col" :name="col" :label="`${col} (${tasks.filter(t => t.status === col).length})`" />
      </q-tabs>
      <q-list separator>
        <q-item v-for="t in tasks.filter(tsk => tsk.status === mobileCol)" :key="t.id"
                clickable @click="openEdit(t)" :class="'priority-' + (t.priority || 'normale').toLowerCase()">
          <q-item-section>
            <q-item-label caption class="text-primary text-weight-bold">{{ t.code }}</q-item-label>
            <q-item-label>{{ t.title }}</q-item-label>
            <q-item-label caption>
              <span v-if="t.project_name">📁 {{ t.project_name }}</span>
              <span v-if="t.assignee_name" class="q-ml-sm">👤 {{ t.assignee_name }}</span>
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-chip dense :label="t.priority" :color="priorityColor(t.priority)" text-color="white" size="sm" />
          </q-item-section>
        </q-item>
      </q-list>
    </div>

    <!-- Create/Edit dialog -->
    <q-dialog v-model="showDialog">
      <q-card style="min-width:400px;max-width:500px">
        <q-card-section class="text-h6">{{ editing ? 'Modifier ' + editing.code : 'Nouvelle tâche' }}</q-card-section>
        <q-card-section>
          <q-input v-model="form.title" label="Titre *" outlined dense class="q-mb-sm" :rules="[v => !!v || 'Requis']" autofocus />
          <q-input v-model="form.description" label="Description" outlined dense type="textarea" rows="2" class="q-mb-sm" />
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-select v-model="form.project_code" :options="projectOptions" label="Projet *" outlined dense
                        use-input @filter="filterProjects" hide-selected fill-input emit-value map-options />
            </div>
            <div class="col-6">
              <q-select v-model="form.status" :options="columns" label="Statut" outlined dense />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-6">
              <q-select v-model="form.priority" :options="['Basse','Normale','Haute','Urgente']" label="Priorité" outlined dense />
            </div>
            <div class="col-6">
              <q-select v-model="form.assigned_to" :options="userOptions" label="Assigné à" outlined dense
                        emit-value map-options />
            </div>
          </div>
          <q-input v-model="form.due_date" label="Échéance" type="date" outlined dense class="q-mt-sm" />
          <q-select v-model="form.email_id" :options="emailOptions" label="Email lié" outlined dense class="q-mt-sm"
                    emit-value map-options clearable />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Annuler" v-close-popup />
          <q-btn v-if="editing" flat color="negative" label="Supprimer" @click="deleteTask" />
          <q-btn color="primary" :label="editing ? 'Mettre à jour' : 'Créer'" @click="saveTask" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()
let sseSource = null
const columns = ['A faire', 'En cours', 'En révision', 'Terminé']
const tasks = ref([])
const mobileCol = ref('A faire')
const showDialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = reactive({ title: '', description: '', project_code: '', status: 'A faire', priority: 'Normale', assigned_to: '', due_date: '', email_id: '' })
const projectOptions = ref([])
const userOptions = ref([])
const emailOptions = ref([])
let draggedTaskId = null

function priorityColor(p) {
  return { 'Basse': 'grey', 'Normale': 'info', 'Haute': 'warning', 'Urgente': 'negative' }[p] || 'grey'
}

async function loadTasks() {
  try {
    const res = await api.get('/tasks')
    tasks.value = res.data.tasks || res.data || []
    // Load options
    const [p, u, e] = await Promise.allSettled([
      api.get('/projects'),
      api.get('/admin/users'),
      api.get('/emails')
    ])
    if (p.status === 'fulfilled') projectOptions.value = (p.value.data.projects || p.value.data || []).map(x => ({ label: x.name, value: x.code }))
    if (u.status === 'fulfilled') userOptions.value = (u.value.data.users || u.value.data || []).map(x => ({ label: x.display_name || x.username, value: x.id }))
    if (e.status === 'fulfilled') emailOptions.value = (e.value.data.emails || e.value.data || []).slice(0, 50).map(x => ({ label: x.subject?.substring(0, 60), value: x.id }))
  } catch {}
}

function filterProjects(val, update) {
  update(() => {})
}

function openCreate() {
  editing.value = null
  Object.assign(form, { title: '', description: '', project_code: '', status: 'A faire', priority: 'Normale', assigned_to: '', due_date: '', email_id: '' })
  showDialog.value = true
}

function openEdit(task) {
  editing.value = task
  Object.assign(form, {
    title: task.title || '', description: task.description || '',
    project_code: task.project_code || '', status: task.status || 'A faire',
    priority: task.priority || 'Normale', assigned_to: task.assigned_to || '',
    due_date: task.due_date?.substring(0, 10) || '', email_id: ''
  })
  showDialog.value = true
}

async function saveTask() {
  saving.value = true
  try {
    const url = editing.value ? `/tasks/api/${editing.value.id}/update` : '/tasks/api/create'
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => fd.append(k, v || ''))
    await api.post(url, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    showDialog.value = false
    loadTasks()
    $q.notify({ type: 'positive', message: editing.value ? 'Tâche mise à jour' : 'Tâche créée' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erreur' })
  } finally {
    saving.value = false
  }
}

async function deleteTask() {
  try {
    await api.delete(`/tasks/${editing.value.id}`)
    showDialog.value = false
    loadTasks()
    $q.notify({ type: 'positive', message: 'Tâche supprimée' })
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Erreur suppression' })
  }
}

function onDragStart(ev, taskId) {
  draggedTaskId = taskId
  ev.dataTransfer.effectAllowed = 'move'
}

async function onDrop(ev, newStatus) {
  if (!draggedTaskId) return
  try {
    await api.post(`/tasks/${draggedTaskId}/status`, { status: newStatus })
    draggedTaskId = null
    loadTasks()
  } catch {}
}

onMounted(() => {
  loadTasks()
  // SSE pour mises à jour Kanban en temps réel
  sseSource = new EventSource('/notifications/stream')
  sseSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.event === 'tasks.updated') loadTasks()
    } catch {}
  }
})

onUnmounted(() => {
  if (sseSource) sseSource.close()
})
</script>
