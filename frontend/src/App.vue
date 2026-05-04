<template>
  <router-view />
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useAuthStore } from './stores/auth'
import { initPushNotifications } from './boot/push'

const auth = useAuthStore()
onMounted(() => {
  auth.checkAuth()
})

// Init push quand l'utilisateur est connecté
watch(() => auth.user, (user) => {
  if (user) initPushNotifications()
}, { immediate: true })
</script>
