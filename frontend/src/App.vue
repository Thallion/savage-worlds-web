<template>
  <v-app>
    <v-app-bar color="primary" density="compact">
      <v-app-bar-title>Savage Worlds Charakter-Generator</v-app-bar-title>
      <template v-if="authStore.isLoggedIn">
        <v-btn to="/" variant="text" prepend-icon="mdi-account-group">Charaktere</v-btn>
        <v-btn to="/settings" variant="text" prepend-icon="mdi-book-cog">Settings</v-btn>
        <v-chip class="mr-2 ml-2" variant="outlined">{{ authStore.user?.benutzername }}</v-chip>
        <v-btn icon="mdi-logout" @click="logout" />
      </template>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const snackbar = reactive({ show: false, text: '', color: 'success' })

async function logout() {
  authStore.logout()
  router.push('/login')
}
</script>
