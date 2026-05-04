<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn flat dense round icon="menu" @click="drawer = !drawer" class="lt-md" />
        <q-toolbar-title @click="$router.push('/')" style="cursor:pointer">
          📧 MailApp
        </q-toolbar-title>
        <q-btn flat dense round icon="logout" @click="doLogout" title="Déconnexion" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="drawer" show-if-above :width="200" :breakpoint="600" bordered>
      <q-list padding dense>
        <q-item-label header class="text-caption">{{ auth.user?.display_name || auth.user?.username }}</q-item-label>

        <q-item clickable v-ripple to="/" exact dense>
          <q-item-section avatar><q-icon name="dashboard" size="xs" /></q-item-section>
          <q-item-section class="text-caption">Dashboard</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/projects" dense>
          <q-item-section avatar><q-icon name="folder" size="xs" /></q-item-section>
          <q-item-section class="text-caption">Projets</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/tasks" dense>
          <q-item-section avatar><q-icon name="assignment" size="xs" /></q-item-section>
          <q-item-section class="text-caption">Tâches</q-item-section>
        </q-item>

        <q-separator spaced />

        <q-expansion-item
          expand-separator
          default-opened
          dense
          icon="email"
          label="Emails"
          header-class="text-caption"
        >
          <q-item clickable v-ripple to="/emails" exact dense class="q-pl-lg">
            <q-item-section avatar><q-icon name="inbox" size="xs" /></q-item-section>
            <q-item-section class="text-caption">Boîte de réception</q-item-section>
          </q-item>

          <q-item clickable v-ripple to="/drafts" dense class="q-pl-lg">
            <q-item-section avatar><q-icon name="drafts" size="xs" /></q-item-section>
            <q-item-section class="text-caption">Brouillons</q-item-section>
          </q-item>

          <q-item clickable v-ripple to="/sent" dense class="q-pl-lg">
            <q-item-section avatar><q-icon name="send" size="xs" /></q-item-section>
            <q-item-section class="text-caption">Envoyés</q-item-section>
          </q-item>

          <q-item clickable v-ripple to="/compose" dense class="q-pl-lg">
            <q-item-section avatar><q-icon name="edit" size="xs" color="primary" /></q-item-section>
            <q-item-section class="text-caption">Nouveau message</q-item-section>
          </q-item>
        </q-expansion-item>

        <q-separator spaced />

        <q-item clickable v-ripple to="/documents" dense>
          <q-item-section avatar><q-icon name="description" size="xs" /></q-item-section>
          <q-item-section class="text-caption">Documents</q-item-section>
        </q-item>

        <template v-if="auth.isAdmin">
          <q-separator spaced />
          <q-item-label header class="text-caption">Administration</q-item-label>
          <q-item clickable v-ripple to="/admin/users" dense>
            <q-item-section avatar><q-icon name="people" size="xs" /></q-item-section>
            <q-item-section class="text-caption">Utilisateurs</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/admin/invitations" dense>
            <q-item-section avatar><q-icon name="mail_outline" size="xs" /></q-item-section>
            <q-item-section class="text-caption">Invitations</q-item-section>
          </q-item>
        </template>
      </q-list>
    </q-drawer>

    <q-page-container>
      <q-page padding>
        <router-view />
      </q-page>
    </q-page-container>

  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const drawer = ref(false)

function doLogout() {
  auth.logout()
  router.push('/login')
}
</script>
