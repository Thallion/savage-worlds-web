<template>
  <v-card flat>
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="profil.Name"
            label="Name"
            @update:model-value="updateProfil"
          />
          <v-text-field
            v-model="profil.Konzept"
            label="Konzept"
            @update:model-value="updateProfil"
          />
          <v-text-field
            v-model="profil.Alter"
            label="Alter"
            @update:model-value="updateProfil"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="profil.Geschlecht"
            label="Geschlecht"
            @update:model-value="updateProfil"
          />
          <v-text-field
            v-model="profil.Sprachen"
            label="Sprachen"
            @update:model-value="updateProfil"
          />
          <v-select
            v-model="settingAuswahl"
            :items="einstellungenStore.verfuegbareSettings"
            item-title="name"
            item-value="name"
            label="Setting"
            @update:model-value="frageSettingWechsel"
          />
        </v-col>
      </v-row>

      <v-dialog v-model="dialogSichtbar" max-width="480">
        <v-card>
          <v-card-title>Setting wechseln?</v-card-title>
          <v-card-text>
            Beim Wechsel zu <strong>{{ neuesSetting }}</strong> werden Attribute,
            Fertigkeiten, Volk, Handicaps, Talente und Mächte zurückgesetzt.
            Das Profil bleibt erhalten.
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="wechselAbbrechen">Abbrechen</v-btn>
            <v-btn color="primary" variant="tonal" :loading="wechselt" @click="wechselBestaetigen">
              Wechseln
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const profil = computed(() => daten.value.profil_daten)

const settingAuswahl = ref(daten.value.active_setting_name)
watch(
  () => daten.value.active_setting_name,
  (name) => (settingAuswahl.value = name),
)

const dialogSichtbar = ref(false)
const neuesSetting = ref('')
const wechselt = ref(false)
const meldung = ref('')
const meldungSichtbar = ref(false)

function updateProfil() {
  daten.value.profil_daten = { ...profil.value }
}

function frageSettingWechsel(name: string) {
  if (name === daten.value.active_setting_name) return
  neuesSetting.value = name
  dialogSichtbar.value = true
}

function wechselAbbrechen() {
  dialogSichtbar.value = false
  settingAuswahl.value = daten.value.active_setting_name
}

async function wechselBestaetigen() {
  wechselt.value = true
  try {
    const result = await store.spiellogikAktion('setting/wechseln', neuesSetting.value)
    if (result.success) {
      store.aktuellerCharakter!.active_setting_name = neuesSetting.value
      await einstellungenStore.ladeSetting(neuesSetting.value)
    } else {
      settingAuswahl.value = daten.value.active_setting_name
    }
    if (result.message) {
      meldung.value = result.message
      meldungSichtbar.value = true
    }
  } finally {
    wechselt.value = false
    dialogSichtbar.value = false
  }
}
</script>
