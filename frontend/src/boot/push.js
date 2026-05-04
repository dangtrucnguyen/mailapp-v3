// Push notification setup — Web Push (browser) or Tauri native
import api from './api'

const isTauri = !!(window.__TAURI_INTERNALS__)

let swRegistration = null

export async function initPushNotifications() {
  // In Tauri, notifications are handled natively via tauri-plugin-notification
  if (isTauri) {
    console.log('[Push] Tauri native notifications enabled')
    return true
  }

  // Browser: Service Worker + Web Push
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.log('Push notifications not supported')
    return false
  }

  try {
    // Register service worker (handled by vite-plugin-pwa)
    const reg = await navigator.serviceWorker.ready
    if (!reg) return false
    swRegistration = reg

    // Check existing subscription
    let subscription = await reg.pushManager.getSubscription()
    if (subscription) {
      // Already subscribed — refresh on server
      await api.post('/notifications/push/subscribe', { subscription: subscription.toJSON() })
      return true
    }

    // Ask permission
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') return false

    // Get VAPID public key
    const { data } = await api.get('/notifications/push/vapid-public-key')
    const applicationServerKey = urlBase64ToUint8Array(data.public_key)

    // Subscribe
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey
    })

    await api.post('/notifications/push/subscribe', {
      subscription: subscription.toJSON()
    })

    return true
  } catch (err) {
    console.error('Push subscription error:', err)
    return false
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

// Listen for service worker messages (notification clicks)
navigator.serviceWorker?.addEventListener('message', (event) => {
  if (event.data?.type === 'NOTIFICATION_CLICK') {
    const url = event.data.url || '/'
    if (window.location.pathname !== url) {
      window.location.href = url
    }
  }
})
