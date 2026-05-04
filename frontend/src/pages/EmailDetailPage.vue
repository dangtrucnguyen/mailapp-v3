<template>
  <div>
    <q-breadcrumbs class="q-mb-sm">
      <q-breadcrumbs-el label="Emails" to="/emails" />
      <q-breadcrumbs-el :label="email?.subject?.substring(0, 40) || '...'" />
      <q-breadcrumbs-el v-if="isArchived" label="Archivé" class="text-warning" />
    </q-breadcrumbs>

    <div v-if="email">
      <!-- Toolbar -->
      <div class="row items-center justify-between q-mb-md">
        <div class="text-h6 ellipsis" style="max-width:55%">
          {{ email.subject }}
        </div>
        <div class="row q-gutter-xs">
          <q-btn-group unelevated>
            <q-btn dense color="grey-3" text-color="dark" icon="reply" size="sm" @click="doReply" no-caps>
              <q-tooltip>Répondre</q-tooltip>
            </q-btn>
            <q-btn dense color="grey-3" text-color="dark" icon="reply_all" size="sm" @click="doReplyAll" no-caps>
              <q-tooltip>Répondre à tous</q-tooltip>
            </q-btn>
            <q-btn dense color="grey-3" text-color="dark" icon="forward" size="sm" @click="doForward" no-caps>
              <q-tooltip>Transférer</q-tooltip>
            </q-btn>
          </q-btn-group>
          <q-btn dense flat round icon="archive" size="sm" @click="doArchive"
                 :color="isArchived ? 'warning' : 'grey'" :title="isArchived ? 'Désarchiver' : 'Archiver'">
            <q-tooltip>{{ isArchived ? 'Désarchiver' : 'Archiver' }}</q-tooltip>
          </q-btn>
          <q-btn dense flat round icon="delete" size="sm" color="grey" @click="doDelete" title="Supprimer">
            <q-tooltip>Supprimer</q-tooltip>
          </q-btn>
          <q-btn dense flat round icon="more_vert" size="sm">
            <q-menu>
              <q-list dense>
                <q-item clickable v-close-popup @click="doPrint">
                  <q-item-section avatar><q-icon name="print" size="xs" /></q-item-section>
                  <q-item-section>Imprimer</q-item-section>
                </q-item>
                <q-item v-if="!isArchived" clickable v-close-popup @click="doArchive">
                  <q-item-section avatar><q-icon name="archive" size="xs" /></q-item-section>
                  <q-item-section>Archiver</q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="doDelete">
                  <q-item-section avatar><q-icon name="delete" size="xs" /></q-item-section>
                  <q-item-section>Supprimer</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </div>
      </div>

      <!-- En-tête : expéditeur, destinataires, date -->
      <q-card flat bordered class="q-mb-md">
        <q-card-section class="q-py-sm q-px-md">
          <div class="row items-center q-mb-xs">
            <q-avatar size="36px" color="blue-2" text-color="blue-8" class="q-mr-sm">
              {{ (email.sender_name || email.sender || '?').charAt(0).toUpperCase() }}
            </q-avatar>
            <div class="col">
              <div class="text-weight-medium">{{ email.sender_name || email.sender }}</div>
              <div class="text-caption text-grey">{{ email.sender }}</div>
            </div>
            <div class="text-caption text-grey">{{ formatDate(email.date_time) }}</div>
          </div>

          <!-- Destinataires -->
          <div class="q-ml-xl">
            <div class="row items-start text-caption">
              <span class="text-grey q-mr-sm" style="min-width:30px">À:</span>
              <span class="col" style="word-break:break-word">
                <template v-if="recipientsExpanded || recipientsList.length <= 2">
                  {{ email.recipients }}
                </template>
                <template v-else>
                  {{ recipientsList.slice(0, 2).join(', ') }}
                  <q-btn dense flat size="xs" color="primary" no-caps @click="recipientsExpanded = true"
                         icon-right="expand_more" label="Plus..." class="q-ml-xs" />
                </template>
              </span>
            </div>
            <div v-if="email.cc" class="row items-start text-caption q-mt-xs">
              <span class="text-grey q-mr-sm" style="min-width:30px">Cc:</span>
              <span class="col" style="word-break:break-word">{{ email.cc }}</span>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <div class="row q-col-gutter-md">
        <!-- Corps de l'email -->
        <div class="col-12 col-md-8">
          <q-card flat bordered>
            <q-card-section class="q-pa-md">
              <div v-if="email.body_html" v-html="email.body_html"
                   style="max-height:80vh;overflow-y:auto;line-height:1.6"
                   class="email-body-sandbox"></div>
              <div v-else-if="email.body_text"
                   style="white-space:pre-wrap;line-height:1.7;word-break:break-word;font-size:13.5px">
                {{ email.body_text }}
              </div>
              <div v-else class="text-grey text-caption">(Contenu non disponible)</div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Colonne droite : PJ + Projet + Tâches + Détails -->
        <div class="col-12 col-md-4">
          <!-- Pièces jointes -->
          <q-card v-if="attachments.length" flat bordered class="q-mb-sm">
            <q-card-section class="q-pa-sm">
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-caption text-weight-bold">📎 {{ attachments.length }} pièce(s) jointe(s)</div>
                <q-btn dense flat size="sm" icon="file_download" color="primary" no-caps
                       @click="downloadAllAttachments" label="Tout télécharger" />
              </div>
              <q-list dense separator>
                <q-item v-for="att in visibleAttachments" :key="att.filename" dense>
                  <q-item-section avatar>
                    <q-icon :name="fileIcon(att.mime_type)" size="sm" :color="fileColor(att.mime_type)" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-caption ellipsis">{{ att.filename }}</q-item-label>
                    <q-item-label caption>{{ formatSize(att.size) }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-btn dense flat round size="xs" icon="download"
                           @click="downloadAttachment(att.filename)"
                           title="Télécharger" />
                  </q-item-section>
                </q-item>
              </q-list>
              <q-btn v-if="attachments.length > ATTACH_LIMIT && !attachmentsExpanded"
                     flat dense no-caps size="sm" color="primary" class="full-width q-mt-xs"
                     @click="attachmentsExpanded = true"
                     :label="`+ ${attachments.length - ATTACH_LIMIT} autre(s)...`" />
            </q-card-section>
          </q-card>

          <!-- Projet -->
          <q-card flat bordered class="q-mb-sm">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-weight-bold q-mb-xs">🔗 Projet</div>
              <q-select v-model="projectCode" :options="projectOptions" label="Lier à un projet"
                        outlined dense emit-value map-options clearable
                        @update:model-value="linkProject" />
            </q-card-section>
          </q-card>

          <!-- Tâches liées -->
          <q-card flat bordered class="q-mb-sm">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-weight-bold q-mb-xs">📋 Tâches liées</div>
              <q-list dense separator v-if="linkedTasks.length" class="q-pa-none" style="max-height:200px;overflow-y:auto">
                <q-item v-for="t in linkedTasks" :key="t.id" dense clickable @click="$router.push('/tasks')">
                  <q-item-section>
                    <q-item-label class="text-caption">
                      <span class="text-primary text-weight-bold">{{ t.code }}</span>
                      {{ t.title?.substring(0, 50) }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-else class="text-caption text-grey q-mb-sm">Aucune tâche liée</div>
            </q-card-section>
            <q-separator />
            <q-card-section class="q-pa-sm">
              <q-input v-model="taskTitle" label="Titre de la tâche" outlined dense class="q-mb-xs" hide-bottom-space
                       placeholder="[Email] Titre..." />
              <q-select v-model="taskProject" :options="projectOptions" label="Projet" outlined dense
                        emit-value map-options class="q-mb-sm" />
              <q-btn color="primary" icon="add_task" label="Créer une tâche" @click="createTask" :loading="creatingTask"
                     class="full-width" size="sm" dense no-caps />
            </q-card-section>
          </q-card>

          <!-- Détails -->
        </div>
      </div>
    </div>

    <div v-else class="flex flex-center q-pa-xl">
      <q-spinner /><span class="q-ml-sm">Chargement...</span>
    </div>

    <!-- Dialog confirmation suppression -->
    <q-dialog v-model="confirmDelete">
      <q-card>
        <q-card-section class="row items-center">
          <q-icon name="delete" color="negative" size="md" class="q-mr-sm" />
          <span>Supprimer cet email ?</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Annuler" v-close-popup />
          <q-btn flat color="negative" label="Supprimer" @click="doDeleteConfirmed" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const email = ref(null)
const linkedTasks = ref([])
const attachments = ref([])
const projectCode = ref('')
const projectOptions = ref([])
const taskTitle = ref('')
const taskProject = ref('')
const creatingTask = ref(false)
const recipientsExpanded = ref(false)
const confirmDelete = ref(false)
const isArchived = ref(false)
const attachmentsExpanded = ref(false)
const ATTACH_LIMIT = 5

const visibleAttachments = computed(() => {
  if (attachmentsExpanded.value) return attachments.value
  return attachments.value.slice(0, ATTACH_LIMIT)
})

const recipientsList = computed(() => {
  if (!email.value?.recipients) return []
  return email.value.recipients.split(',').map(r => r.trim()).filter(Boolean)
})

function formatDate(d) {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatSize(bytes) {
  if (!bytes) return '0 o'
  const units = ['o', 'Ko', 'Mo', 'Go']
  let i = 0, s = bytes
  while (s >= 1024 && i < units.length - 1) { s /= 1024; i++ }
  return `${s.toFixed(i ? 1 : 0)} ${units[i]}`
}

function fileIcon(mime) {
  if (!mime) return 'description'
  if (mime.includes('pdf')) return 'picture_as_pdf'
  if (mime.includes('image')) return 'image'
  if (mime.includes('sheet') || mime.includes('excel') || mime.includes('xls')) return 'table_chart'
  if (mime.includes('word') || mime.includes('doc')) return 'article'
  if (mime.includes('zip') || mime.includes('rar') || mime.includes('compress')) return 'folder_zip'
  return 'description'
}

function fileColor(mime) {
  if (!mime) return 'grey'
  if (mime.includes('pdf')) return 'negative'
  if (mime.includes('image')) return 'green'
  if (mime.includes('sheet') || mime.includes('excel') || mime.includes('xls')) return 'positive'
  return 'grey'
}

onMounted(async () => {
  try {
    const [er, pr] = await Promise.allSettled([
      api.get(`/emails/${route.params.id}`),
      api.get('/projects')
    ])
    if (er.status === 'fulfilled') {
      email.value = er.value.data.email || er.value.data
      linkedTasks.value = er.value.data.linked_tasks || []
      attachments.value = er.value.data.attachments || er.value.data.email?.attachments || []
      projectCode.value = email.value?.project_code || ''
      isArchived.value = (email.value?.labels || '').includes('archived')

      // Fetch body with inline images converted to data URIs
      if (email.value?.body_html && email.value.body_html.includes('cid:')) {
        try {
          const br = await api.get(`/emails/${route.params.id}/body-html`)
          if (br.data.html) email.value.body_html = br.data.html
        } catch {}
      }
    }
    if (pr.status === 'fulfilled') {
      projectOptions.value = (pr.value.data.projects || pr.value.data || []).map(p => ({ label: p.name, value: p.code }))
    }
  } catch {}
})

function doReply() {
  router.push(`/compose?reply_to=${route.params.id}`)
}

function doReplyAll() {
  router.push(`/compose?reply_to=${route.params.id}&all=1`)
}

function doForward() {
  router.push(`/compose?forward=${route.params.id}`)
}

function doPrint() { window.print() }

async function doArchive() {
  try {
    await api.post(`/emails/${route.params.id}/archive`)
    isArchived.value = !isArchived.value
    $q.notify({ type: 'positive', message: isArchived.value ? 'Email archivé' : 'Email désarchivé', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Erreur' })
  }
}

function doDelete() {
  confirmDelete.value = true
}

async function doDeleteConfirmed() {
  try {
    await api.delete(`/emails/${route.params.id}`)
    $q.notify({ type: 'positive', message: 'Email supprimé', timeout: 1500 })
    router.push('/emails')
  } catch {
    $q.notify({ type: 'negative', message: 'Erreur' })
  } finally {
    confirmDelete.value = false
  }
}

function downloadAttachment(filename) {
  const token = localStorage.getItem('access_token')
  const base = api.defaults.baseURL || ''
  const url = `${base}/emails/${route.params.id}/attachment/${encodeURIComponent(filename)}`
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error('Not found')
      return res.blob()
    })
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(() => $q.notify({ type: 'negative', message: 'Téléchargement échoué' }))
}

function downloadAllAttachments() {
  const token = localStorage.getItem('access_token')
  const base = api.defaults.baseURL || ''
  const url = `${base}/emails/${route.params.id}/attachments/zip`
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error('Failed')
      return res.blob()
    })
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `attachments-${route.params.id.substring(0, 8)}.zip`
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(() => $q.notify({ type: 'negative', message: 'Téléchargement ZIP échoué' }))
}

async function linkProject() {
  try {
    await api.post(`/emails/${route.params.id}/link-project`, { project_code: projectCode.value })
    $q.notify({ type: 'positive', message: 'Projet lié', timeout: 1500 })
  } catch {}
}

async function createTask() {
  if (!taskProject.value) return $q.notify({ type: 'warning', message: 'Sélectionnez un projet' })
  creatingTask.value = true
  try {
    await api.post(`/emails/${route.params.id}/create-task`, {
      title: taskTitle.value || `[Email] ${email.value?.subject?.substring(0, 40)}`,
      project_code: taskProject.value
    })
    $q.notify({ type: 'positive', message: 'Tâche créée', timeout: 1500 })
    taskTitle.value = ''
    taskProject.value = ''
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erreur' })
  } finally {
    creatingTask.value = false
  }
}
</script>

<style scoped>
.email-body-sandbox {
  isolation: isolate;
}
.email-body-sandbox :deep(*) {
  max-width: 100%;
  box-sizing: border-box;
}
.email-body-sandbox :deep(img) {
  max-width: 100%;
  height: auto;
}
</style>
