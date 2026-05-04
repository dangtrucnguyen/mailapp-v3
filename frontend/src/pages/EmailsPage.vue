<template>
  <div class="emails-split">
    <!-- Liste (toujours visible en desktop, plein écran si pas de sélection) -->
    <div class="email-list-pane" :class="{ 'full-width': !selectedEmail }" :style="listPaneStyle">
      <div class="row items-center justify-between q-mb-sm q-px-sm">
        <div class="text-h6">Emails</div>
        <q-btn color="primary" icon="edit" label="Nouveau" size="sm" @click="$router.push('/compose')" />
      </div>

      <!-- Search/filter bar -->
      <div class="q-px-sm q-mb-sm">
        <q-input
          v-model="filter"
          dense
          outlined
          placeholder="Filtrer les emails..."
          debounce="150"
          clearable
        >
          <template #prepend>
            <q-icon name="search" size="xs" />
          </template>
        </q-input>
      </div>

      <q-virtual-scroll
        :items="filteredEmails"
        v-slot="{ item: e, index }"
        class="email-scroll"
        style="height: calc(100vh - 120px)"
      >
        <q-item
          :key="e.id"
          clickable
          v-ripple
          :active="selectedId === e.id"
          active-class="bg-blue-1"
          @click="selectEmail(e)"
          dense
        >
          <q-item-section avatar>
            <q-icon
              name="email"
              :color="e.project_code ? 'primary' : 'grey'"
              size="xs"
            />
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-caption" style="font-weight:500">
              {{ e.sender_name || e.sender?.split('@')[0] }}
            </q-item-label>
            <q-item-label class="ellipsis" style="font-size:12px">
              {{ e.subject }}
            </q-item-label>
            <q-item-label caption style="font-size:10px">
              {{ fmtDate(e.date_time) }}
              <q-badge v-if="e.project_name" color="blue-1" text-color="blue-8" align="middle" style="font-size:8px;padding:1px 4px">
                {{ e.project_name?.substring(0, 15) }}
              </q-badge>
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-virtual-scroll>
    </div>

    <!-- Resizable divider -->
    <div
      v-if="selectedEmail"
      class="split-divider"
      @mousedown.prevent="startResize"
    >
      <div class="divider-handle" />
    </div>

    <!-- Panneau détail (desktop, visible si sélectionné) -->
    <div v-if="selectedEmail" class="email-detail-pane">
      <div v-if="loadingDetail" class="flex flex-center q-pa-xl">
        <q-spinner-dots color="primary" size="40px" />
      </div>

      <template v-else-if="detail">
        <!-- Toolbar -->
        <div class="row items-center q-px-md q-py-sm bg-grey-2">
          <div class="text-subtitle1 ellipsis" style="max-width:50%">
            {{ detail.subject }}
          </div>
          <q-space />
          <div class="row q-gutter-xs">
            <q-btn dense flat round size="sm" icon="reply" @click="doReply" title="Répondre" />
            <q-btn dense flat round size="sm" icon="reply_all" @click="doReplyAll" title="Répondre à tous" />
            <q-btn dense flat round size="sm" icon="forward" @click="doForward" title="Transférer" />
            <q-btn
              dense flat round size="sm"
              :icon="isArchived ? 'unarchive' : 'archive'"
              :color="isArchived ? 'warning' : 'grey-7'"
              @click="doArchive"
              :title="isArchived ? 'Désarchiver' : 'Archiver'"
            />
            <q-btn dense flat round size="sm" icon="delete" color="negative" @click="confirmDelete = true" title="Supprimer" />
          </div>
        </div>

        <!-- En-tête -->
        <div class="q-px-md q-py-sm">
          <div class="row items-baseline">
            <div class="text-body2 text-bold">{{ detail.sender_name || detail.sender }}</div>
            <div class="text-caption text-grey q-ml-sm">{{ detail.sender?.includes('@') ? detail.sender : '' }}</div>
          </div>
          <div class="row">
            <div class="text-caption text-grey-7">
              À : {{ fmtRecipients(detail.recipients) }}
              <template v-if="detail.cc">
                · Cc : {{ detail.cc?.substring(0, 60) }}
              </template>
            </div>
          </div>
          <div class="text-caption text-grey-5 q-mt-xs">{{ fmtFullDate(detail.date_time) }}</div>
        </div>

        <q-separator />

        <!-- Corps -->
        <div class="email-body-scroll q-pa-md">
          <div v-if="detail.body_html" ref="emailBodyRef" class="email-body-sandbox"></div>
          <div v-else-if="detail.body_text" style="white-space:pre-wrap;line-height:1.7;word-break:break-word;font-size:13px">
            {{ detail.body_text }}
          </div>
          <div v-else class="text-grey text-caption">(Contenu non disponible)</div>
        </div>

        <!-- Pièces jointes -->
        <template v-if="attachments.length">
          <q-separator />
          <div class="q-px-md q-py-sm">
            <div class="row items-center q-mb-sm">
              <div class="text-caption text-bold text-grey-8">Pièces jointes ({{ attachments.length }})</div>
              <q-space />
              <q-btn dense flat size="sm" icon="download" label="Tout" @click="downloadAll" no-caps />
            </div>
            <div class="row q-gutter-sm">
              <div
                v-for="att in visibleAttachments"
                :key="att.filename"
                class="attachment-chip"
                @click="downloadOne(att)"
              >
                <q-icon :name="attIcon(att.mime_type)" size="xs" class="q-mr-xs" />
                <span class="text-caption ellipsis" style="max-width:140px">{{ att.filename }}</span>
                <span class="text-caption text-grey-6 q-ml-xs">({{ fmtSize(att.size) }})</span>
              </div>
              <q-btn
                v-if="attachments.length > 5 && !attachmentsExpanded"
                dense flat size="sm"
                :label="'+ ' + (attachments.length - 5) + ' autre(s)'"
                no-caps
                @click="attachmentsExpanded = true"
              />
              <q-btn
                v-if="attachmentsExpanded && attachments.length > 5"
                dense flat size="sm"
                label="Réduire"
                no-caps
                @click="attachmentsExpanded = false"
              />
            </div>
          </div>
        </template>

        <!-- Projet lié -->
        <q-separator />
        <div class="q-px-md q-py-sm row items-center q-gutter-sm">
          <span class="text-caption text-grey-7">Projet :</span>
          <q-select
            v-model="projectCode"
            :options="projectOptions"
            dense
            outlined
            style="min-width:180px"
            placeholder="Choisir..."
            clearable
            @update:model-value="linkProject"
          />
        </div>
      </template>
    </div>

    <!-- Confirm delete -->
    <q-dialog v-model="confirmDelete" persistent>
      <q-card style="min-width:300px">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="sm" class="q-mr-sm" />
          <span>Supprimer cet email ?</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Annuler" v-close-popup />
          <q-btn flat color="negative" label="Supprimer" @click="doDelete" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../boot/api'

const route = useRoute()
const router = useRouter()
const emails = ref([])
const filter = ref('')
const filteredEmails = computed(() => {
  const q = filter.value.toLowerCase()
  if (!q) return emails.value
  return emails.value.filter(e =>
    (e.subject || '').toLowerCase().includes(q) ||
    (e.sender || '').toLowerCase().includes(q) ||
    (e.sender_name || '').toLowerCase().includes(q) ||
    (e.snippet || '').toLowerCase().includes(q)
  )
})
const selectedId = ref(null)
const detail = ref(null)
const attachments = ref([])
const loadingDetail = ref(false)
const projectCode = ref('')
const projectOptions = ref([])
const confirmDelete = ref(false)
const isArchived = ref(false)
const attachmentsExpanded = ref(false)
const emailBodyRef = ref(null)
const listWidth = ref(38)
const isResizing = ref(false)

const listPaneStyle = computed(() => ({
  width: selectedEmail.value ? listWidth.value + '%' : '100%',
  minWidth: '220px',
}))

const visibleAttachments = computed(() => {
  if (attachments.value.length <= 5 || attachmentsExpanded.value) return attachments.value
  return attachments.value.slice(0, 5)
})

onMounted(async () => {
  try {
    const res = await api.get('/emails?mailbox=inbox')
    emails.value = res.data.emails || res.data || []
  } catch {}

  // Restore selection from URL param
  if (route.query.id) {
    const e = emails.value.find(x => x.id === route.query.id)
    if (e) selectEmail(e)
    else {
      // Try loading by id directly
      selectedId.value = route.query.id
      await loadDetail(route.query.id)
    }
  }
})

async function selectEmail(e) {
  // If already selected on desktop, keep it (don't toggle)
  if (selectedId.value === e.id && selectedEmail.value) return

  selectedId.value = e.id
  selectedEmail.value = e
  await loadDetail(e.id)

  // Update URL without navigation
  router.replace({ query: { id: e.id } })
}

async function loadDetail(id) {
  loadingDetail.value = true
  selectedEmail.value = emails.value.find(e => e.id === id) || selectedEmail.value

  try {
    const res = await api.get(`/emails/${id}`)
    detail.value = res.data.email || res.data
    attachments.value = res.data.attachments || res.data.email?.attachments || []
    projectCode.value = detail.value?.project_code || ''
    isArchived.value = (detail.value?.labels || '').includes('archived')

    // Fetch body-html for cid: images
    if (detail.value?.body_html && detail.value.body_html.includes('cid:')) {
      try {
        const br = await api.get(`/emails/${id}/body-html`)
        if (br.data.html) detail.value.body_html = br.data.html
      } catch {}
    }

    // Load project options (don't block rendering)
    api.get('/projects').then(pr => {
      projectOptions.value = (pr.data.projects || pr.data || []).map(p => ({ label: p.name || p.code, value: p.code }))
    }).catch(() => {})

    // Show detail NOW, then render shadow DOM
    loadingDetail.value = false
    await nextTick()
    renderEmailBody()
  } catch {
    detail.value = null
    loadingDetail.value = false
  }
}

// Shadow DOM — same as EmailDetailPage
function renderEmailBody() {
  const el = emailBodyRef.value
  if (!el || !detail.value?.body_html) return

  let html = detail.value.body_html || ''
  if (!html.trim()) return

  const styleBlocks = []
  html = html.replace(/<style[^>]*>([\s\S]*?)<\/style>/gi, (match, css) => {
    styleBlocks.push(css)
    return ''
  })

  html = html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/ on\w+="[^"]*"/gi, '')

  let shadow = el.shadowRoot
  if (!shadow) shadow = el.attachShadow({ mode: 'open' })

  shadow.innerHTML = `
    <style>
      :host { all: initial; display: block; font-family: inherit; font-size: inherit; color: inherit; line-height: inherit; }
      :host img { max-width: 100% !important; height: auto !important; }
    </style>
    ${styleBlocks.map(css => `<style>${css}</style>`).join('\n')}
    ${html}
  `
}

watch(() => detail.value?.body_html, async (newVal) => {
  if (newVal) { await nextTick(); renderEmailBody() }
})

// Actions
function doReply() {
  if (selectedId.value) router.push(`/compose?reply_to=${selectedId.value}`)
}
function doReplyAll() {
  if (selectedId.value) router.push(`/compose?reply_to=${selectedId.value}&all=1`)
}
function doForward() {
  if (selectedId.value) router.push(`/compose?forward=${selectedId.value}`)
}
async function doArchive() {
  try {
    await api.post(`/emails/${selectedId.value}/archive`)
    isArchived.value = !isArchived.value
  } catch {}
}
async function doDelete() {
  try {
    await api.delete(`/emails/${selectedId.value}`)
    emails.value = emails.value.filter(e => e.id !== selectedId.value)
    selectedEmail.value = null
    detail.value = null
    router.replace({ query: {} })
  } catch {}
}
async function linkProject(code) {
  if (!selectedId.value) return
  try {
    await api.post(`/emails/${selectedId.value}/link-project`, { project_code: code || '' })
  } catch {}
}
async function downloadAll() {
  try {
    const res = await api.get(`/emails/${selectedId.value}/attachments/zip`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'attachments.zip'
    a.click()
    URL.revokeObjectURL(url)
  } catch {}
}
async function downloadOne(att) {
  try {
    const res = await api.get(`/emails/${selectedId.value}/attachment/${encodeURIComponent(att.filename)}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = att.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {}
}

// Resize
function startResize(e) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = listWidth.value

  function onMove(ev) {
    const containerWidth = document.querySelector('.emails-split')?.offsetWidth || window.innerWidth
    const dx = ev.clientX - startX
    const newPct = startWidth + (dx / containerWidth) * 100
    if (newPct >= 20 && newPct <= 60) {
      listWidth.value = Math.round(newPct)
    }
  }

  function onUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

// Helpers
function fmtDate(d) {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}
function fmtFullDate(d) {
  if (!d) return ''
  const date = new Date(d)
  return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) +
    ' à ' + date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
function fmtRecipients(rec) {
  if (!rec) return ''
  // Extract first 2 recipients
  const parts = rec.split(';').slice(0, 2).map(r => r.trim().substring(0, 30))
  const more = rec.split(';').length > 2 ? ` +${rec.split(';').length - 2}` : ''
  return parts.join(', ') + more
}
function fmtSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' o'
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' Ko'
  return (bytes / 1048576).toFixed(1) + ' Mo'
}
function attIcon(mime) {
  if (!mime) return 'attach_file'
  if (mime.includes('pdf')) return 'picture_as_pdf'
  if (mime.includes('image')) return 'image'
  if (mime.includes('sheet') || mime.includes('excel') || mime.includes('xls')) return 'table_chart'
  if (mime.includes('zip')) return 'folder_zip'
  if (mime.includes('word') || mime.includes('document')) return 'article'
  return 'attach_file'
}
</script>

<style scoped>
.emails-split {
  display: flex;
  height: calc(100vh - 80px);
  gap: 0;
}

.email-list-pane {
  width: 38%;
  min-width: 220px;
  border-right: none;
  overflow: hidden;
  transition: none;
}
.email-list-pane.full-width {
  width: 100%;
  border-right: none;
}

.email-detail-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.email-body-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
}

.attachment-chip {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  cursor: pointer;
  transition: background 0.15s;
  max-width: 200px;
}
.attachment-chip:hover {
  background: #f5f5f5;
}

.split-divider {
  width: 6px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  flex-shrink: 0;
}
.split-divider:hover,
.split-divider:active {
  background: #e0e0e0;
}
.divider-handle {
  width: 2px;
  height: 32px;
  border-radius: 2px;
  background: #ccc;
  transition: background 0.15s;
}
.split-divider:hover .divider-handle {
  background: #999;
}

/* Mobile: stack vertically */
@media (max-width: 768px) {
  .emails-split {
    flex-direction: column;
  }
  .email-list-pane {
    width: 100%;
    border-right: none;
  }
  .email-detail-pane {
    width: 100%;
  }
}
</style>
