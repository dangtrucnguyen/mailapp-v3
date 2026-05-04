<template>
  <div class="search-container">
    <q-input
      v-model="query"
      dense
      outlined
      placeholder="Rechercher..."
      class="search-input"
      debounce="300"
      @update:model-value="onSearch"
      @focus="focused = true"
      @blur="onBlur"
      clearable
      bg-color="white"
    >
      <template #prepend>
        <q-icon name="search" />
      </template>
      <template #append>
        <q-spinner v-if="loading" size="16px" />
      </template>
    </q-input>

    <!-- Results dropdown -->
    <div v-if="focused && (results.length || searched)" class="search-results" @mousedown.prevent>
      <!-- Category tabs — desktop: horizontal, mobile: select -->
      <div class="gt-xs row q-pa-sm q-gutter-xs">
        <q-btn
          v-for="tab in tabs"
          :key="tab.key"
          :label="tab.label + (counts[tab.key] ? ' (' + counts[tab.key] + ')' : '')"
          :color="activeTab === tab.key ? 'primary' : 'grey-7'"
          :flat="activeTab !== tab.key"
          dense
          size="sm"
          no-caps
          @click="activeTab = tab.key"
        />
      </div>
      <div class="lt-sm q-pa-sm">
        <q-select
          v-model="activeTab"
          :options="tabs"
          option-value="key"
          option-label="label"
          dense
          outlined
          emit-value
          map-options
        />
      </div>

      <!-- Results list -->
      <div class="results-scroll">
        <template v-if="filteredResults.length">
          <q-item
            v-for="r in filteredResults"
            :key="r.category + r.id"
            clickable
            v-ripple
            dense
            @click="openResult(r)"
          >
            <q-item-section avatar>
              <q-icon :name="catIcon(r.category)" :color="catColor(r.category)" size="sm" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-caption" v-html="highlightMatch(r.title)" />
              <q-item-label caption class="text-grey-7" style="font-size:11px">
                <span v-if="r.subtitle">{{ r.subtitle?.substring(0, 40) }} · </span>
                <span>{{ fmtDate(r.date) }}</span>
                <q-badge v-if="r.category === 'projects' && r.email_count" color="blue-1" text-color="blue-8" class="q-ml-xs" style="font-size:9px">
                  {{ r.email_count }} email{{ r.email_count > 1 ? 's' : '' }}
                </q-badge>
                <span v-if="r.category === 'attachments'" class="text-grey">
                  · {{ fmtSize(r.size) }}
                </span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="catColor(r.category)" text-color="white" style="font-size:9px" :label="catLabel(r.category)" />
            </q-item-section>
          </q-item>
        </template>
        <div v-else class="text-center q-pa-md text-grey-6 text-caption">
          Aucun résultat pour "{{ query }}"
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../boot/api'

const router = useRouter()
const query = ref('')
const results = ref([])
const searched = ref(false)
const loading = ref(false)
const focused = ref(false)
const activeTab = ref('all')

const tabs = [
  { key: 'all', label: 'Tous' },
  { key: 'emails', label: 'Emails' },
  { key: 'projects', label: 'Projets' },
  { key: 'attachments', label: 'Fichiers' },
]

const counts = computed(() => {
  const c = {}
  for (const t of tabs) c[t.key] = 0
  for (const r of results.value) {
    c[r.category] = (c[r.category] || 0) + 1
    c.all = (c.all || 0) + 1
  }
  return c
})

const filteredResults = computed(() => {
  if (activeTab.value === 'all') return results.value
  return results.value.filter(r => r.category === activeTab.value)
})

let searchTimer = null

function onSearch(val) {
  clearTimeout(searchTimer)
  if (!val || val.length < 2) {
    results.value = []
    searched.value = false
    return
  }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await api.get('/search', { params: { q: val, limit: 8 } })
      results.value = res.data.results || []
      searched.value = true
    } catch (e) {
      console.error('Search error:', e)
    }
    loading.value = false
  }, 350)
}

function onBlur() {
  // Delay hide to allow click on results
  setTimeout(() => { focused.value = false }, 200)
}

function openResult(r) {
  focused.value = false
  query.value = ''
  results.value = []

  switch (r.category) {
    case 'emails':
      router.push(`/emails/${r.id}`)
      break
    case 'projects':
      router.push(`/projects/${r.id}`)
      break
    case 'attachments':
      // Navigate to the parent email
      router.push(`/emails/${r.email_hash}`)
      break
    default:
      break
  }
}

function catIcon(cat) {
  return { emails: 'email', projects: 'folder', attachments: 'attach_file' }[cat] || 'search'
}

function catColor(cat) {
  return { emails: 'primary', projects: 'orange', attachments: 'teal' }[cat] || 'grey'
}

function catLabel(cat) {
  return { emails: 'Email', projects: 'Projet', attachments: 'Fichier' }[cat] || cat
}

function fmtDate(d) {
  if (!d) return ''
  return d.substring(0, 16).replace('T', ' ')
}

function fmtSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' o'
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' Ko'
  return (bytes / 1048576).toFixed(1) + ' Mo'
}

function highlightMatch(text) {
  if (!text) return ''
  // Keep existing <b> highlights from FTS5 snippet, otherwise bold the query
  if (text.includes('<b>')) return text
  const q = query.value.trim()
  if (!q) return text
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(`(${escaped})`, 'gi'), '<b>$1</b>')
}
</script>

<style scoped>
.search-container {
  position: relative;
  max-width: 420px;
  width: 100%;
  margin: 0 8px;
}

.search-input :deep(.q-field__control) {
  height: 36px;
}
.search-input :deep(.q-field__native) {
  padding: 0 4px;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 0 0 8px 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  z-index: 2000;
  min-width: 360px;
}

.results-scroll {
  max-height: 420px;
  overflow-y: auto;
}
</style>
