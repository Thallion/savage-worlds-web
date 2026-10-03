import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { istGastId } from '@/utils/gastCharaktere'

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
      path: '/kampf',
      name: 'kampfsimulator',
      component: () => import('@/views/KampfsimulatorView.vue'),
    },
    {
      path: '/charakter/:id',
      name: 'charakter-editor',
      component: () => import('@/views/CharakterEditorView.vue'),
      // Gast-Charaktere (negative ID, im Browser gespeichert) gehen ohne Login
      meta: { requiresAuth: true, gastCharakterErlaubt: true },
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  const istGastCharakter = to.meta.gastCharakterErlaubt && istGastId(Number(to.params.id))
  if (to.meta.requiresAuth && !istGastCharakter && !authStore.isLoggedIn) {
    return { name: 'login' }
  }
})

export default router
