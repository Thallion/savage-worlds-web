import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
    },
    {
      path: '/info',
      name: 'info',
      component: () => import('@/views/InfoView.vue'),
    },
    {
      path: '/impressum',
      name: 'impressum',
      component: () => import('@/views/ImpressumView.vue'),
    },
    {
      path: '/datenschutz',
      name: 'datenschutz',
      component: () => import('@/views/DatenschutzView.vue'),
    },
    {
      path: '/',
      name: 'charakterliste',
      component: () => import('@/views/CharakterListeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/konto',
      name: 'konto',
      component: () => import('@/views/KontoView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'setting-verwaltung',
      component: () => import('@/views/SettingVerwaltungView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/charakter/:id',
      name: 'charakter-editor',
      component: () => import('@/views/CharakterEditorView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return { name: 'login' }
  }
})

export default router
