<template>
  <div>
    <div class="row items-center justify-between q-mb-md">
      <div class="text-h5">Projets</div>
      <q-btn color="primary" icon="add" label="Nouveau projet" @click="showCreate = true" />
    </div>

    <div class="row q-col-gutter-md">
      <div v-for="p in projects" :key="p.code" class="col-12 col-sm-6 col-md-4">
        <q-card flat bordered class="card-hover" @click="$router.push(`/projects/${p.code}`)">
          <q-card-section>
            <div class="text-subtitle1">{{ p.name }}</div>
            <div class="text-caption text-grey">{{ p.code }} · {{ p.status }}</div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <div class="text-body2">{{ p.description || 'Aucune description' }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div v-if="!projects.length" class="text-center q-pa-xl text-grey">
      <q-icon name="folder_off" size="48px" />
      <p>Aucun projet pour le moment</p>
    </div>

    <!-- Create dialog -->
    <q-dialog v-model="showCreate">
      <q-card style="min-width:400px">
        <q-card-section class="text-h6">Nouveau projet</q-card-section>
        <q-card-section>
          <q-input v-model="form.name" label="Nom du projet *" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis']" autofocus />
          <q-input v-model="form.code" label="Code (ex: 24-016-TEST)" outlined dense class="q-mb-sm"
                   :rules="[v => !!v || 'Requis']" />
          <q-input v-model="form.description" label="Description" outlined dense type="textarea" rows="2" class="q-mb-sm" />
          <q-select v-model="form.status" :options="['Actif','En pause','Terminé','Archivé']" label="Statut" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Annuler" v-close-popup />
          <q-btn color="primary" label="Créer" @click="createProject" :loading="creating" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const router = useRouter()
const projects = ref([])
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ name: '', code: '', description: '', status: 'Actif' })

async function loadProjects() {
  try {
    const res = await api.get('/projects')
    projects.value = Array.isArray(res.data) ? res.data : (res.data.projects || [])
  } catch {}
}

async function createProject() {
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.name)
    fd.append('code', form.code)
    fd.append('description', form.description)
    fd.append('status', form.status)
    await api.post('/projects/create', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    showCreate.value = false
    Object.assign(form, { name: '', code: '', description: '', status: 'Actif' })
    loadProjects()
    $q.notify({ type: 'positive', message: 'Projet créé' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erreur' })
  } finally {
    creating.value = false
  }
}

onMounted(loadProjects)
</script>
