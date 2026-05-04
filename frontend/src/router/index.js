import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../pages/LoginPage.vue'), meta: { guest: true } },
  { path: '/register', name: 'Register', component: () => import('../pages/RegisterPage.vue'), meta: { guest: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../pages/DashboardPage.vue') },
      { path: 'projects', name: 'Projects', component: () => import('../pages/ProjectsPage.vue') },
      { path: 'projects/:code', name: 'ProjectDetail', component: () => import('../pages/ProjectDetailPage.vue'), props: true },
      { path: 'tasks', name: 'Tasks', component: () => import('../pages/TasksPage.vue') },
      { path: 'emails', name: 'Emails', component: () => import('../pages/EmailsPage.vue') },
      { path: 'emails/:id', name: 'EmailDetail', component: () => import('../pages/EmailDetailPage.vue'), props: true },
      { path: 'compose', name: 'Compose', component: () => import('../pages/ComposePage.vue') },
      { path: 'drafts', name: 'Drafts', component: () => import('../pages/DraftsPage.vue') },
      { path: 'sent', name: 'Sent', component: () => import('../pages/SentPage.vue') },
      { path: 'admin/users', name: 'AdminUsers', component: () => import('../pages/AdminUsersPage.vue'), meta: { admin: true } },
      { path: 'admin/invitations', name: 'AdminInvitations', component: () => import('../pages/AdminInvitationsPage.vue'), meta: { admin: true } },
      { path: 'documents', name: 'Documents', component: () => import('../pages/DocumentsPage.vue') }
    ]
  },
  { path: '/accept-invitation', name: 'AcceptInvitation', component: () => import('../pages/AcceptInvitationPage.vue'), meta: { guest: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  await auth.checkAuth()

  if (to.meta.requiresAuth && !auth.user) return next('/login')
  if (to.meta.guest && auth.user) return next('/')
  if (to.meta.admin && auth.user?.role !== 'admin') return next('/')
  next()
})

export default router
