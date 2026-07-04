<template>
  <v-container v-if="store.aktuellerCharakter" fluid>
    <v-row class="mb-2" align="center">
      <v-col cols="auto">
        <v-btn icon="mdi-arrow-left" variant="text" @click="router.push('/')" />
      </v-col>
      <v-col>
        <h2 class="text-h5">{{ daten.profil_daten?.Name || 'Neuer Charakter' }}</h2>
        <span class="text-caption">{{ store.aktuellerCharakter.active_setting_name }}</span>
      </v-col>
      <v-col cols="auto" class="d-flex ga-2">
        <v-btn
          v-if="!erschaffungAbgeschlossen"
          color="success"
          variant="tonal"
          prepend-icon="mdi-check-decagram"
          @click="abschlussDialog = true"
        >
          Erschaffung abschließen
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-content-save" @click="speichern" :loading="saving">
          Speichern
        </v-btn>
      </v-col>
    </v-row>

    <!-- Punktebudget-Leiste (Erschaffung) -->
    <v-card v-if="!erschaffungAbgeschlossen" class="mb-4" density="compact">
      <v-card-text class="d-flex ga-4 flex-wrap">
        <v-chip :color="(daten.verbleibende_attributsteigerungen ?? 5) > 0 ? 'primary' : 'success'">
          Attribute: {{ daten.verbleibende_attributsteigerungen ?? 5 }}
        </v-chip>
        <v-chip :color="(daten.verbleibende_fertigkeitssteigerungen ?? 12) > 0 ? 'primary' : 'success'">
          Fertigkeiten: {{ daten.verbleibende_fertigkeitssteigerungen ?? 12 }}
        </v-chip>
        <v-chip :color="(daten.verbleibende_handicap_punkte ?? 0) > 0 ? 'primary' : 'success'">
          Handicap-Punkte: {{ daten.verbleibende_handicap_punkte ?? 0 }} frei
          ({{ daten.gesamt_handicap_punkte ?? 0 }}/4 gewählt)
        </v-chip>
        <v-chip :color="(daten.verbleibende_talente ?? 0) > 0 ? 'primary' : 'secondary'">
          Talent-Slots: {{ daten.verbleibende_talente ?? 0 }}
        </v-chip>
        <v-chip v-if="zeigeMaechte" color="secondary">
          Mächte: {{ store.abgeleiteteWerte?.verbleibende_maechte ?? 0 }} frei
        </v-chip>
      </v-card-text>
    </v-card>

    <!-- Aufstiegs-Leiste (nach der Erschaffung) -->
    <v-card v-else class="mb-4" density="compact">
      <v-card-text class="d-flex ga-4 flex-wrap align-center">
        <v-chip color="success" prepend-icon="mdi-medal">
          Rang: {{ store.abgeleiteteWerte?.rang ?? 'Anfänger' }}
        </v-chip>
        <div class="d-flex align-center ga-1">
          <v-btn
            icon="mdi-minus"
            size="x-small"
            variant="outlined"
            @click="aufstiegAktion('aufstieg/entfernen')"
          />
          <v-chip :color="(daten.verbleibende_aufstiege ?? 0) > 0 ? 'primary' : 'secondary'">
            Aufstiege: {{ daten.verbleibende_aufstiege ?? 0 }} frei
            ({{ daten.aufstiege_gesamt ?? 0 }} gesamt)
          </v-chip>
          <v-btn
            icon="mdi-plus"
            size="x-small"
            variant="outlined"
            color="primary"
            @click="aufstiegAktion('aufstieg/hinzufuegen')"
          />
        </div>
        <v-chip v-if="zeigeMaechte" color="secondary">
          Mächte: {{ store.abgeleiteteWerte?.verbleibende_maechte ?? 0 }} frei
        </v-chip>
        <v-spacer />
        <v-btn size="small" variant="text" prepend-icon="mdi-lock-open" @click="erschaffungOeffnen">
          Erschaffung wieder öffnen
        </v-btn>
      </v-card-text>
    </v-card>

    <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

    <v-dialog v-model="abschlussDialog" max-width="520">
      <v-card>
        <v-card-title>Erschaffung abschließen?</v-card-title>
        <v-card-text>
          Danach kosten Steigerungen Aufstiege (1 Aufstieg = 1 Attribut, 2
          Fertigkeitssteigerungen oder 1 Talent) und der Rang steigt mit den
          ausgegebenen Aufstiegen. Handicap-Punkte können nicht mehr ausgegeben
          werden. Der Schritt lässt sich wieder öffnen.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="abschlussDialog = false">Abbrechen</v-btn>
          <v-btn color="success" variant="tonal" @click="erschaffungAbschliessen">
            Abschließen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-tabs v-model="activeTab" color="primary" grow>
      <v-tab value="profil">Profil</v-tab>
      <v-tab value="voelker">Volk</v-tab>
      <v-tab value="eigenschaften">Eigenschaften</v-tab>
      <v-tab value="handicaps">Handicaps</v-tab>
      <v-tab value="talente">Talente</v-tab>
      <v-tab v-if="zeigeMaechte" value="maechte">Mächte</v-tab>
      <v-tab value="ausruestung">Ausrüstung</v-tab>
      <v-tab v-if="zeigeCyberware" value="cyberware">Cyberware</v-tab>
      <v-tab v-if="zeigeSuperkraefte" value="superkraefte">Superkräfte</v-tab>
      <v-tab value="uebersicht">Übersicht</v-tab>
    </v-tabs>

    <v-tabs-window v-model="activeTab" class="mt-4">
      <v-tabs-window-item value="profil">
        <ProfilTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="voelker">
        <VoelkerTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="eigenschaften">
        <EigenschaftenTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="handicaps">
        <HandicapsTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="talente">
        <TalenteTab />
      </v-tabs-window-item>
      <v-tabs-window-item v-if="zeigeMaechte" value="maechte">
        <MaechteTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="ausruestung">
        <AusruestungTab />
      </v-tabs-window-item>
      <v-tabs-window-item v-if="zeigeCyberware" value="cyberware">
        <CyberwareTab />
      </v-tabs-window-item>
      <v-tabs-window-item v-if="zeigeSuperkraefte" value="superkraefte">
        <SuperkraefteTab />
      </v-tabs-window-item>
      <v-tabs-window-item value="uebersicht">
        <UebersichtTab />
      </v-tabs-window-item>
    </v-tabs-window>
  </v-container>

  <v-container v-else class="text-center pa-8">
    <v-progress-circular indeterminate color="primary" size="64" />
    <p class="mt-4">Charakter wird geladen...</p>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import ProfilTab from '@/components/charakter/ProfilTab.vue'
import VoelkerTab from '@/components/charakter/VoelkerTab.vue'
import EigenschaftenTab from '@/components/charakter/EigenschaftenTab.vue'
import HandicapsTab from '@/components/charakter/HandicapsTab.vue'
import TalenteTab from '@/components/charakter/TalenteTab.vue'
import MaechteTab from '@/components/charakter/MaechteTab.vue'
import AusruestungTab from '@/components/charakter/AusruestungTab.vue'
import CyberwareTab from '@/components/charakter/CyberwareTab.vue'
import SuperkraefteTab from '@/components/charakter/SuperkraefteTab.vue'
import UebersichtTab from '@/components/charakter/UebersichtTab.vue'

const route = useRoute()
const router = useRouter()
const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const activeTab = ref('profil')
const saving = ref(false)
const abschlussDialog = ref(false)
const meldung = ref('')
const meldungSichtbar = ref(false)

const daten = computed(() => store.aktuellerCharakter?.charakter_daten ?? ({} as any))
const erschaffungAbgeschlossen = computed(() => daten.value.char_gen_completed === true)

// Mächte-Tab nur bei arkanem Hintergrund (AH-Talent gewählt oder Mächte vorhanden)
const zeigeMaechte = computed(() => {
  const w = store.abgeleiteteWerte
  return (
    (w?.machtpunkte ?? 0) > 0 ||
    (w?.verbleibende_maechte ?? 0) > 0 ||
    (daten.value.selected_maechte?.length ?? 0) > 0
  )
})

// Setting-Spezialsysteme: /berechne liefert die Blöcke nur, wenn das Setting sie kennt
const zeigeCyberware = computed(() => store.abgeleiteteWerte?.cyberware != null)
const zeigeSuperkraefte = computed(() => store.abgeleiteteWerte?.superkraefte != null)

onMounted(async () => {
  const id = Number(route.params.id)
  await store.ladeCharakter(id)
  if (store.aktuellerCharakter) {
    await einstellungenStore.ladeSetting(store.aktuellerCharakter.active_setting_name)
  }
})

async function speichern() {
  saving.value = true
  try {
    await store.speichereCharakter()
  } finally {
    saving.value = false
  }
}

async function erschaffungAbschliessen() {
  abschlussDialog.value = false
  const result = await store.spiellogikAktion('erschaffung/abschliessen')
  if (result.success) {
    // char_gen_completed liegt auch als Spalte auf der Charakter-Zeile
    store.aktuellerCharakter!.char_gen_completed = true
  } else if (result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function erschaffungOeffnen() {
  const result = await store.spiellogikAktion('erschaffung/oeffnen')
  if (result.success) {
    store.aktuellerCharakter!.char_gen_completed = false
  } else if (result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}

async function aufstiegAktion(aktion: string) {
  const result = await store.spiellogikAktion(aktion)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
