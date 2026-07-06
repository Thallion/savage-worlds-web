<template>
  <v-app>
    <v-app-bar color="primary" density="compact">
      <v-app-bar-title>Savage Worlds Charakter-Generator</v-app-bar-title>
      <v-spacer />
      <template v-if="authStore.isLoggedIn">
        <v-btn to="/" variant="text" prepend-icon="mdi-account-group">Charaktere</v-btn>
        <v-btn to="/settings" variant="text" prepend-icon="mdi-book-cog">Settings</v-btn>
        <v-chip class="mr-2 ml-2" variant="outlined">{{ authStore.user?.benutzername }}</v-chip>
      </template>
      <v-btn to="/info" variant="text" icon="mdi-information-outline" title="Info" />
      <theme-manager />
      <v-btn v-if="authStore.isLoggedIn" icon="mdi-logout" @click="logout" />
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <v-footer color="surface-variant" class="justify-center py-2">
      <v-btn to="/info" variant="text" size="small" class="text-none">Info</v-btn>
      <v-btn to="/impressum" variant="text" size="small" class="text-none">Impressum</v-btn>
      <v-btn to="/datenschutz" variant="text" size="small" class="text-none">Datenschutz</v-btn>
    </v-footer>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import ThemeManager from '@/components/ThemeManager.vue'

const authStore = useAuthStore()
const router = useRouter()
const snackbar = reactive({ show: false, text: '', color: 'success' })

// Theme- und Farbeinstellungen aus dem Store auf Vuetify anwenden.
const vuetifyTheme = useTheme()
const themeStore = useThemeStore()

function wendeThemeAn() {
  const id = themeStore.themeId
  vuetifyTheme.change(id)

  // Aktive Primärfarbe (benutzerdefinierter Akzent oder Theme-Standard) setzen.
  const colors = vuetifyTheme.themes.value[id]?.colors
  if (colors) {
    colors.primary = themeStore.aktivePrimaerfarbe(id)
  }

  // Pergament-Themes markieren, damit die Textur greift.
  document.body.classList.toggle('sw-pergament', id === 'pergament')
  document.body.classList.toggle('sw-pergamentDunkel', id === 'pergamentDunkel')

  // Browser-Chrome (mobil) an die App-Bar-Farbe angleichen.
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', themeStore.aktivePrimaerfarbe(id))
}

watch(() => [themeStore.themeId, themeStore.akzentfarbe], wendeThemeAn, { immediate: true })

async function logout() {
  authStore.logout()
  router.push('/login')
}
</script>
