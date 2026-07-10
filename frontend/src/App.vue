<template>
  <v-app>
    <!--
      Navigations-Schublade nur für schmale Screens (Hochkant-Smartphone). Auf
      größeren Screens bleibt die volle App-Bar; auf kleinen wandern Titel-Links,
      Benutzer und Abmelden hierher, damit die App-Bar nicht überläuft.
    -->
    <v-navigation-drawer v-if="mobile" v-model="drawer" temporary location="left">
      <v-list nav>
        <v-list-item
          v-if="authStore.isLoggedIn"
          prepend-icon="mdi-account"
          :title="authStore.user?.benutzername"
          subtitle="Angemeldet"
        />
        <v-divider v-if="authStore.isLoggedIn" class="mb-2" />
        <template v-if="authStore.isLoggedIn">
          <v-list-item to="/" prepend-icon="mdi-account-group" title="Charaktere" @click="drawer = false" />
          <v-list-item to="/settings" prepend-icon="mdi-book-cog" title="Settings" @click="drawer = false" />
        </template>
        <v-list-item to="/info" prepend-icon="mdi-information-outline" title="Info" @click="drawer = false" />
        <template v-if="authStore.isLoggedIn">
          <v-divider class="my-2" />
          <v-list-item prepend-icon="mdi-logout" title="Abmelden" @click="logout" />
        </template>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar color="primary" density="compact">
      <v-app-bar-nav-icon v-if="mobile" @click="drawer = !drawer" />
      <v-app-bar-title>Savage Worlds Charakter-Generator</v-app-bar-title>
      <v-spacer />
      <template v-if="!mobile">
        <template v-if="authStore.isLoggedIn">
          <v-btn to="/" variant="text" prepend-icon="mdi-account-group">Charaktere</v-btn>
          <v-btn to="/settings" variant="text" prepend-icon="mdi-book-cog">Settings</v-btn>
          <v-chip class="mr-2 ml-2" variant="outlined">{{ authStore.user?.benutzername }}</v-chip>
        </template>
        <v-btn to="/info" variant="text" icon="mdi-information-outline" title="Info" />
      </template>
      <theme-manager />
      <v-btn v-if="!mobile && authStore.isLoggedIn" icon="mdi-logout" @click="logout" />
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
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme, useDisplay } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import ThemeManager from '@/components/ThemeManager.vue'

const authStore = useAuthStore()
const router = useRouter()
const snackbar = reactive({ show: false, text: '', color: 'success' })

// Schmale Screens (Hochkant-Smartphone / kleine Tablets) bekommen die
// Navigations-Schublade statt der breiten Button-Leiste.
const { smAndDown: mobile } = useDisplay()
const drawer = ref(false)

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
