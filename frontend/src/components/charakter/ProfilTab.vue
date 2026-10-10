<template>
  <v-card flat>
    <v-card-text>
      <v-row>
        <!-- Porträt: wirkt sofort auf dem Server, nur mit Konto -->
        <v-col cols="12" md="3" class="d-flex flex-column align-center">
          <div
            class="portraet-flaeche"
            :class="{ aktiv: ziehtDrueber, bedienbar: !store.aktuellIstGast }"
            :title="store.aktuellIstGast ? undefined : 'Bild hierher ziehen oder klicken'"
            @dragover.prevent="ziehtDrueber = !store.aktuellIstGast"
            @dragleave="ziehtDrueber = false"
            @drop.prevent="beimDrop"
            @click="!store.aktuellIstGast && oeffneBildDialog(!charakter.bild_id)"
          >
            <CharakterPortraet
              :bild-id="charakter.bild_id"
              :name="profil.Name || charakter.char_name"
              variante="gross"
              :breite="200"
            />
          </div>
          <template v-if="!store.aktuellIstGast">
            <div class="d-flex flex-wrap justify-center ga-1 mt-2">
              <v-btn
                size="small"
                variant="tonal"
                prepend-icon="mdi-upload"
                @click="oeffneBildDialog(true)"
              >
                {{ charakter.bild_id ? 'Neues Bild' : 'Bild hochladen' }}
              </v-btn>
              <template v-if="charakter.bild_id">
                <v-btn
                  size="small"
                  variant="text"
                  icon="mdi-crop"
                  title="Ausschnitt ändern"
                  @click="oeffneBildDialog(false)"
                />
                <v-btn
                  size="small"
                  variant="text"
                  color="error"
                  icon="mdi-delete"
                  title="Bild entfernen"
                  :loading="entferntBild"
                  @click="entferneBild"
                />
              </template>
            </div>
          </template>
          <div v-else class="text-caption text-medium-emphasis text-center mt-2" style="max-width: 200px">
            Porträts gibt es mit Konto — melde dich an, um ein Bild hochzuladen.
          </div>
        </v-col>

        <v-col cols="12" md="9">
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
        </v-col>
      </v-row>

      <BildHochladenDialog
        v-if="!store.aktuellIstGast"
        v-model="bildDialogOffen"
        :charakter-id="charakter.id"
        :bestehendes-bild="bildDialogNeu ? null : charakter.bild_id"
        :bestehender-fokus="charakter.bild_fokus_y"
        :datei="bildDatei"
      />

      <v-dialog v-model="dialogSichtbar" max-width="480">
        <v-card>
          <v-card-title>Setting wechseln?</v-card-title>
          <v-card-text>
            Beim Wechsel zu <strong>{{ neuesSetting }}</strong> werden Attribute,
            Fertigkeiten, Abstammung, Handicaps, Talente und Mächte zurückgesetzt.
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
import BildHochladenDialog from './BildHochladenDialog.vue'
import CharakterPortraet from './CharakterPortraet.vue'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const charakter = computed(() => store.aktuellerCharakter!)
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

// ---- Porträt ----
const bildDialogOffen = ref(false)
const bildDialogNeu = ref(true)
const bildDatei = ref<File | null>(null)
const ziehtDrueber = ref(false)
const entferntBild = ref(false)

function oeffneBildDialog(neu: boolean, datei: File | null = null) {
  bildDialogNeu.value = neu
  bildDatei.value = datei
  bildDialogOffen.value = true
}

function beimDrop(e: DragEvent) {
  ziehtDrueber.value = false
  const datei = e.dataTransfer?.files?.[0]
  if (datei && !store.aktuellIstGast) oeffneBildDialog(true, datei)
}

async function entferneBild() {
  entferntBild.value = true
  try {
    await store.entferneBild(charakter.value.id)
  } catch (e) {
    meldung.value = e instanceof Error ? e.message : 'Bild konnte nicht entfernt werden.'
    meldungSichtbar.value = true
  } finally {
    entferntBild.value = false
  }
}

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

<style scoped>
.portraet-flaeche {
  border-radius: 8px;
  outline: 2px dashed transparent;
  outline-offset: 4px;
  transition: outline-color 0.15s;
}
.portraet-flaeche.bedienbar {
  cursor: pointer;
}
.portraet-flaeche.bedienbar:hover,
.portraet-flaeche.aktiv {
  outline-color: rgb(var(--v-theme-primary));
}
</style>
