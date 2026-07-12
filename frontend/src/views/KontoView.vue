<template>
  <v-container class="fill-height" fluid>
    <v-row justify="center">
      <v-col cols="12" sm="8" md="5">
        <v-card class="pa-4 mb-4">
          <v-card-title class="text-h5">Konto</v-card-title>
          <v-card-subtitle v-if="authStore.user">
            Angemeldet als {{ authStore.user.benutzername }} ({{ authStore.user.email }})
          </v-card-subtitle>
        </v-card>

        <!-- Passwort ändern -->
        <v-card class="pa-4 mb-4">
          <v-card-title class="text-h6">Passwort ändern</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handlePasswortAendern">
              <v-text-field
                v-model="aktuellesPasswort"
                label="Aktuelles Passwort"
                type="password"
                prepend-inner-icon="mdi-lock"
                required
              />
              <v-text-field
                v-model="neuesPasswort"
                label="Neues Passwort"
                type="password"
                prepend-inner-icon="mdi-lock-plus"
                required
              />
              <v-text-field
                v-model="neuesPasswortBestaetigung"
                label="Neues Passwort bestätigen"
                type="password"
                prepend-inner-icon="mdi-lock-check"
                required
              />
              <v-alert v-if="pwError" type="error" class="mb-4" density="compact">
                {{ pwError }}
              </v-alert>
              <v-alert v-if="pwSuccess" type="success" class="mb-4" density="compact">
                Passwort erfolgreich geändert.
              </v-alert>
              <v-btn type="submit" color="primary" :loading="pwLoading">Passwort ändern</v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- Account löschen -->
        <v-card class="pa-4" variant="outlined" color="error">
          <v-card-title class="text-h6">Account löschen</v-card-title>
          <v-card-text>
            <p class="mb-4 text-body-2">
              Dein Account und alle deine Charaktere, Ordner und Settings werden
              unwiderruflich gelöscht.
            </p>
            <v-btn color="error" variant="flat" prepend-icon="mdi-delete" @click="loeschDialog = true">
              Account löschen
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Bestätigungsdialog -->
    <v-dialog v-model="loeschDialog" max-width="440">
      <v-card class="pa-2">
        <v-card-title class="text-h6">Account wirklich löschen?</v-card-title>
        <v-card-text>
          <p class="mb-4 text-body-2">
            Diese Aktion kann nicht rückgängig gemacht werden. Gib zur Bestätigung
            dein Passwort ein.
          </p>
          <v-text-field
            v-model="loeschPasswort"
            label="Passwort"
            type="password"
            prepend-inner-icon="mdi-lock"
            @keyup.enter="handleAccountLoeschen"
          />
          <v-alert v-if="loeschError" type="error" class="mb-2" density="compact">
            {{ loeschError }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="loeschDialog = false">Abbrechen</v-btn>
          <v-btn color="error" variant="flat" :loading="loeschLoading" @click="handleAccountLoeschen">
            Endgültig löschen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

// ---- Passwort ändern ----
const aktuellesPasswort = ref('')
const neuesPasswort = ref('')
const neuesPasswortBestaetigung = ref('')
const pwError = ref('')
const pwSuccess = ref(false)
const pwLoading = ref(false)

async function handlePasswortAendern() {
  pwError.value = ''
  pwSuccess.value = false

  if (neuesPasswort.value !== neuesPasswortBestaetigung.value) {
    pwError.value = 'Neue Passwörter stimmen nicht überein'
    return
  }

  pwLoading.value = true
  try {
    await authStore.passwortAendern(aktuellesPasswort.value, neuesPasswort.value)
    pwSuccess.value = true
    aktuellesPasswort.value = ''
    neuesPasswort.value = ''
    neuesPasswortBestaetigung.value = ''
  } catch (e: any) {
    pwError.value = e.message || 'Passwort konnte nicht geändert werden'
  } finally {
    pwLoading.value = false
  }
}

// ---- Account löschen ----
const loeschDialog = ref(false)
const loeschPasswort = ref('')
const loeschError = ref('')
const loeschLoading = ref(false)

async function handleAccountLoeschen() {
  loeschError.value = ''
  loeschLoading.value = true
  try {
    await authStore.accountLoeschen(loeschPasswort.value)
    router.push('/login')
  } catch (e: any) {
    loeschError.value = e.message || 'Account konnte nicht gelöscht werden'
  } finally {
    loeschLoading.value = false
  }
}
</script>
