import { createApp } from 'vue'
import { Quasar, Notify, Dialog, Loading } from 'quasar'
import quasarLang from 'quasar/lang/fr'
import quasarIconSet from 'quasar/icon-set/svg-material-icons-outlined'

// SVG Material Icons - NO font dependency, NO CDN, pure inline SVG
import 'quasar/src/css/index.sass'
import './css/app.scss'

import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { initPushNotifications } from './boot/push'

// ─── Icon Map Function ────────────────────────────────────────────────────
// Resolves icon names to inline SVG from @quasar/extras
import {
  outlinedDashboard, outlinedLogout, outlinedFolder, outlinedAssignment,
  outlinedEmail, outlinedEdit, outlinedDrafts, outlinedSend, outlinedDescription,
  outlinedPeople, outlinedMenu, outlinedReply, outlinedForward, outlinedPrint,
  outlinedAddTask, outlinedAddCircle, outlinedDelete, outlinedClose, outlinedDownload,
  outlinedAttachFile, outlinedCreateNewFolder, outlinedPersonAdd, outlinedMailOutline,
  outlinedBookmark, outlinedArchive, outlinedSearch, outlinedFilterList, outlinedInbox,
  outlinedAdd, outlinedCheck, outlinedStar, outlinedSettings, outlinedError,
  outlinedMoreVert, outlinedReplyAll, outlinedFolderOff, outlinedInsertDriveFile,
  outlinedManageAccounts, outlinedToggleOn,
  outlinedChevronRight, outlinedKeyboardArrowDown, outlinedKeyboardArrowUp,
  outlinedArrowDropDown, outlinedMoreHoriz, outlinedFileDownload, outlinedUploadFile,
  outlinedExpandMore, outlinedImage, outlinedPictureAsPdf, outlinedTableChart,
  outlinedFolderZip, outlinedArticle
} from '@quasar/extras/material-icons-outlined'

const svgIcons = {
  dashboard: outlinedDashboard,
  logout: outlinedLogout,
  folder: outlinedFolder,
  assignment: outlinedAssignment,
  email: outlinedEmail,
  edit: outlinedEdit,
  drafts: outlinedDrafts,
  send: outlinedSend,
  description: outlinedDescription,
  people: outlinedPeople,
  menu: outlinedMenu,
  reply: outlinedReply,
  forward: outlinedForward,
  print: outlinedPrint,
  add_task: outlinedAddTask,
  add_circle: outlinedAddCircle,
  delete: outlinedDelete,
  close: outlinedClose,
  download: outlinedDownload,
  attach_file: outlinedAttachFile,
  create_new_folder: outlinedCreateNewFolder,
  person_add: outlinedPersonAdd,
  mail_outline: outlinedMailOutline,
  bookmark: outlinedBookmark,
  archive: outlinedArchive,
  search: outlinedSearch,
  filter_list: outlinedFilterList,
  inbox: outlinedInbox,
  add: outlinedAdd,
  check: outlinedCheck,
  star: outlinedStar,
  settings: outlinedSettings,
  error: outlinedError,
  more_vert: outlinedMoreVert,
  reply_all: outlinedReplyAll,
  folder_off: outlinedFolderOff,
  insert_drive_file: outlinedInsertDriveFile,
  // Aliases (kebab-case)
  'add-task': outlinedAddTask,
  'add-circle': outlinedAddCircle,
  'attach-file': outlinedAttachFile,
  'create-new-folder': outlinedCreateNewFolder,
  'person-add': outlinedPersonAdd,
  'mail-outline': outlinedMailOutline,
  'filter-list': outlinedFilterList,
  'reply-all': outlinedReplyAll,
  'folder-off': outlinedFolderOff,
  'insert-drive-file': outlinedInsertDriveFile,
  'more-vert': outlinedMoreVert,
  manage_accounts: outlinedManageAccounts,
  toggle_on: outlinedToggleOn,
  chevron_right: outlinedChevronRight,
  keyboard_arrow_down: outlinedKeyboardArrowDown,
  keyboard_arrow_up: outlinedKeyboardArrowUp,
  arrow_drop_down: outlinedArrowDropDown,
  more_horiz: outlinedMoreHoriz,
  file_download: outlinedFileDownload,
  upload_file: outlinedUploadFile,
  expand_more: outlinedExpandMore,
  'expand-more': outlinedExpandMore,
  image: outlinedImage,
  picture_as_pdf: outlinedPictureAsPdf,
  'picture-as-pdf': outlinedPictureAsPdf,
  table_chart: outlinedTableChart,
  'table-chart': outlinedTableChart,
  folder_zip: outlinedFolderZip,
  'folder-zip': outlinedFolderZip,
  article: outlinedArticle,
}

function iconMapFn(iconName) {
  const svg = svgIcons[iconName]
  if (svg) {
    return { icon: svg }
  }
  // Return undefined to let Quasar use default fallback (Material Icons font)
}

const app = createApp(App)
app.use(Quasar, {
  lang: quasarLang,
  iconSet: quasarIconSet,
  plugins: { Notify, Dialog, Loading },
  config: {
    iconMapFn,
    notify: { position: 'top', timeout: 3000 },
    loading: { spinner: 'QSpinnerBars', message: 'Chargement...' }
  }
})
app.use(createPinia())
app.use(router)
app.mount('#app')
