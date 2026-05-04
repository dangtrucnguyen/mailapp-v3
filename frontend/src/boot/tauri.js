/** Tauri integration — configures API base URL for desktop builds */
import { boot } from 'quasar/wrappers'

export default boot(({ app }) => {
  const isTauri = !!(window.__TAURI_INTERNALS__)

  if (isTauri) {
    import('@tauri-apps/api/core').then(({ invoke }) => {
      invoke('get_api_url').then((apiUrl) => {
        app.config.globalProperties.$apiBaseUrl = apiUrl
        localStorage.setItem('mailapp_api_url', apiUrl)
      })
    }).catch(() => {
      app.config.globalProperties.$apiBaseUrl = 'http://192.168.1.242:6000'
    })
  } else {
    const stored = localStorage.getItem('mailapp_api_url')
    app.config.globalProperties.$apiBaseUrl = stored || 'http://192.168.1.242:6000'
  }
})
