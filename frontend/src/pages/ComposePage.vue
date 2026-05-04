<template>
  <div>
    <div class="text-h5 q-mb-md">{{ isReply ? '↩️ Répondre' : isForward ? '↗️ Transférer' : draftId ? '✏️ Brouillon' : '✉️ Nouveau message' }}</div>

    <div v-if="originalEmail" class="q-mb-md">
      <q-banner rounded class="bg-grey-2">
        <strong>{{ isReply ? 'Réponse à' : 'Transfert de' }} :</strong> {{ originalEmail.subject }}<br>
        <span class="text-caption">De: {{ originalEmail.sender }} · {{ originalEmail.date_time?.substring(0, 16) }}</span>
      </q-banner>
    </div>

    <q-form @submit="send">
      <q-input v-model="form.to" label="À *" outlined dense class="q-mb-sm" :rules="[v => !!v || 'Requis']" autofocus />
      <q-input v-model="form.cc" label="CC" outlined dense class="q-mb-sm" />
      <q-input v-model="form.subject" label="Sujet *" outlined dense class="q-mb-sm" :rules="[v => !!v || 'Requis']" />
      <q-input v-model="form.body" label="Message" outlined type="textarea" rows="10" class="q-mb-md" />

      <div class="row q-gutter-sm justify-end">
        <q-btn outline label="💾 Brouillon" @click="saveDraft" :loading="loading" />
        <q-btn color="primary" label="📤 Envoyer" type="submit" :loading="loading" />
      </div>
    </q-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../boot/api'
import { useQuasar } from 'quasar'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const loading = ref(false)
const originalEmail = ref(null)

const replyTo = computed(() => route.query.reply_to || '')
const forward = computed(() => route.query.forward || '')
const draftId = computed(() => route.query.draft || '')
const isReply = computed(() => !!replyTo.value)
const isForward = computed(() => !!forward.value)

const form = reactive({ to: '', cc: '', subject: '', body: '' })

onMounted(async () => {
  if (isReply.value || isForward.value) {
    try {
      const emailId = replyTo.value || forward.value
      const res = await api.get(`/emails/${emailId}`)
      originalEmail.value = res.data.email || res.data
      if (isReply.value) {
        form.to = originalEmail.value.sender || ''
        form.subject = ((originalEmail.value.subject || '').startsWith('Re:') ? '' : 'Re: ') + (originalEmail.value.subject || '')
        form.body = `\n\n--- Message original ---\nDe: ${originalEmail.value.sender}\nDate: ${originalEmail.value.date_time}\nSujet: ${originalEmail.value.subject}\n\n${originalEmail.value.body_text || ''}`
      } else {
        form.subject = ((originalEmail.value.subject || '').startsWith('Fwd:') ? '' : 'Fwd: ') + (originalEmail.value.subject || '')
        form.body = `\n\n--- Message transféré ---\nDe: ${originalEmail.value.sender}\nDate: ${originalEmail.value.date_time}\nSujet: ${originalEmail.value.subject}\n\n${originalEmail.value.body_text || ''}`
      }
    } catch {}
  }
  if (draftId.value) {
    try {
      const res = await api.get(`/emails/drafts/${draftId.value}`)
      const d = res.data.draft || res.data
      if (d) {
        form.to = d.to_email || ''
        form.cc = d.cc || ''
        form.subject = d.subject || ''
        form.body = d.body_text || ''
      }
    } catch {}
  }
})

async function doSend(action) {
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('to', form.to)
    fd.append('cc', form.cc)
    fd.append('subject', form.subject)
    fd.append('body', form.body)
    fd.append('action', action)
    if (draftId.value) fd.append('draft_id', draftId.value)
    if (originalEmail.value) fd.append('reply_to_message_id', originalEmail.value.id || '')
    await api.post('/emails/send', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    $q.notify({ type: 'positive', message: action === 'draft' ? 'Brouillon sauvegardé' : 'Email envoyé' })
    router.push(action === 'draft' ? '/drafts' : '/sent')
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Erreur' })
  } finally {
    loading.value = false
  }
}

function send() { doSend('send') }
function saveDraft() { doSend('draft') }
</script>
