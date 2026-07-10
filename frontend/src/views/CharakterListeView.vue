<template>
  <v-container>
    <v-row class="mb-4" align="center">
      <v-col cols="12" sm="">
        <h1 class="text-h4">Meine Charaktere</h1>
      </v-col>
      <v-col cols="12" sm="auto" class="d-flex flex-wrap ga-2">
        <v-btn variant="tonal" prepend-icon="mdi-upload" @click="importDatei?.click()">
          Importieren
        </v-btn>
        <v-btn variant="tonal" prepend-icon="mdi-folder-plus" @click="ordnerDialogOeffnen()">
          Neuer Ordner
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="dialogOffen = true">
          Neuer Charakter
        </v-btn>
        <input
          ref="importDatei"
          type="file"
          accept="application/json,.json"
          class="d-none"
          @change="importiereDatei"
        />
      </v-col>
    </v-row>

    <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

    <v-progress-linear v-if="store.loading" indeterminate color="primary" />

    <!-- Gar keine Charaktere -->
    <v-row v-if="store.liste.length === 0 && !store.loading">
      <v-col>
        <v-card class="pa-8 text-center">
          <v-icon size="64" color="grey">mdi-account-plus</v-icon>
          <p class="text-h6 mt-4">Noch keine Charaktere vorhanden</p>
          <p class="text-body-2 text-grey">Erstelle deinen ersten Charakter!</p>
        </v-card>
      </v-col>
    </v-row>

    <!-- Ohne Ordner angelegt: flache Liste wie bisher. -->
    <v-row v-if="!hatOrdner">
      <v-col v-for="char in store.liste" :key="char.id" cols="12" sm="6" md="4">
        <charakter-karte
          :char="char"
          :ordner-liste="store.ordnerListe"
          @oeffnen="router.push(`/charakter/${char.id}`)"
          @exportieren="store.exportiereCharakter(char.id, char.char_name)"
          @loeschen="deleteChar(char.id)"
          @verschieben="(ordnerId) => verschiebe(char, ordnerId)"
        />
      </v-col>
    </v-row>

    <!-- Mit Ordnern: einklappbare Sektionen (standardmäßig zu) → Ordner-Übersicht. -->
    <div v-else class="d-flex justify-end mb-2">
      <v-btn size="small" variant="text" @click="alleUmschalten">
        {{ alleOffen ? 'Alle zuklappen' : 'Alle aufklappen' }}
      </v-btn>
    </div>
    <v-expansion-panels v-if="hatOrdner" v-model="offenePanels" multiple>
      <v-expansion-panel v-for="gruppe in gruppen" :key="gruppe.id ?? 'ohne'" :value="gruppe.id ?? 'ohne'">
        <v-expansion-panel-title>
          <v-icon class="mr-3">{{ gruppe.id === null ? 'mdi-folder-outline' : 'mdi-folder' }}</v-icon>
          <span class="text-subtitle-1 font-weight-medium">{{ gruppe.name }}</span>
          <v-chip size="small" class="ml-3" variant="tonal">{{ gruppe.chars.length }}</v-chip>
          <v-spacer />
          <template v-if="gruppe.id !== null">
            <v-btn
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              class="mr-1"
              @click.stop="ordnerDialogOeffnen(gruppe)"
            />
            <v-btn
              icon="mdi-delete"
              size="x-small"
              variant="text"
              color="error"
              class="mr-2"
              @click.stop="loescheOrdner(gruppe)"
            />
          </template>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p v-if="gruppe.chars.length === 0" class="text-body-2 text-grey">
            Keine Charaktere in diesem Ordner.
          </p>
          <v-row v-else>
            <v-col v-for="char in gruppe.chars" :key="char.id" cols="12" sm="6" md="4">
              <charakter-karte
                :char="char"
                :ordner-liste="store.ordnerListe"
                @oeffnen="router.push(`/charakter/${char.id}`)"
                @exportieren="store.exportiereCharakter(char.id, char.char_name)"
                @loeschen="deleteChar(char.id)"
                @verschieben="(ordnerId) => verschiebe(char, ordnerId)"
              />
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Archetypen-Bibliothek: schreibgeschützte Vorlagen aus dem Original, für alle. -->
    <div v-if="store.archetypenOrdner.length" class="mt-8">
      <div class="d-flex align-center mb-1">
        <v-icon class="mr-2">mdi-bookshelf</v-icon>
        <h2 class="text-h5">Archetypen-Bibliothek</h2>
        <v-icon size="small" class="ml-2" color="grey">mdi-lock</v-icon>
      </div>
      <p class="text-body-2 text-grey mb-3">
        Vorlagen aus dem Original – schreibgeschützt. Zum Verwenden „Duplizieren", das legt
        eine editierbare Kopie in deinen Charakteren an.
      </p>

      <v-expansion-panels v-model="archetypPanels" multiple>
        <v-expansion-panel
          v-for="gruppe in archetypenNachSetting"
          :key="gruppe.setting"
          :value="gruppe.setting"
        >
          <v-expansion-panel-title>
            <v-icon class="mr-3">mdi-folder-star</v-icon>
            <span class="text-subtitle-1 font-weight-medium">{{ gruppe.setting }}</span>
            <v-chip size="small" class="ml-3" variant="tonal">{{ gruppe.anzahl }}</v-chip>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row>
              <v-col v-for="a in gruppe.archetypen" :key="a.id" cols="12" sm="6" md="4">
                <v-card variant="tonal">
                  <v-card-title class="text-body-1">{{ a.name }}</v-card-title>
                  <v-card-subtitle>{{ a.setting }}</v-card-subtitle>
                  <v-card-actions>
                    <v-spacer />
                    <v-btn
                      variant="text"
                      prepend-icon="mdi-content-copy"
                      @click="dupliziere(a)"
                    >
                      Duplizieren
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>

    <!-- Neuer Charakter -->
    <v-dialog v-model="dialogOffen" max-width="500">
      <v-card>
        <v-card-title>Neuer Charakter</v-card-title>
        <v-card-text>
          <v-text-field v-model="neuerName" label="Name" autofocus />
          <v-select
            v-model="neuesSetting"
            :items="einstellungenStore.verfuegbareSettings"
            item-title="name"
            item-value="name"
            label="Setting"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialogOffen = false">Abbrechen</v-btn>
          <v-btn color="primary" @click="erstelleNeuenCharakter">Erstellen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Ordner anlegen / umbenennen -->
    <v-dialog v-model="ordnerDialogOffen" max-width="500">
      <v-card>
        <v-card-title>{{ ordnerBearbeitenId === null ? 'Neuer Ordner' : 'Ordner umbenennen' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="ordnerName"
            label="Ordnername"
            autofocus
            @keyup.enter="speichereOrdner"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="ordnerDialogOffen = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!ordnerName.trim()" @click="speichereOrdner">
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'
import { ApiError } from '@/api/client'
import type { Archetyp, CharakterListItem } from '@/types/charakter'
import CharakterKarte from '@/components/charakter/CharakterKarte.vue'

const router = useRouter()
const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const dialogOffen = ref(false)
const neuerName = ref('')
const neuesSetting = ref('SWAE')
const importDatei = ref<HTMLInputElement>()
const meldung = ref('')
const meldungSichtbar = ref(false)

// Ordner-Dialog: null = anlegen, sonst umbenennen.
const ordnerDialogOffen = ref(false)
const ordnerName = ref('')
const ordnerBearbeitenId = ref<number | null>(null)

const hatOrdner = computed(() => store.ordnerListe.length > 0)

// Offene Expansion-Panels (Panel-Wert = Ordner-id bzw. 'ohne'). Leer = alles zu
// → liefert die kompakte Ordner-Übersicht.
const offenePanels = ref<(number | string)[]>([])

interface Gruppe {
  id: number | null
  name: string
  chars: CharakterListItem[]
}

// Charaktere nach Ordner gruppieren. Ordner immer anzeigen (auch leere), damit
// man Charaktere hineinschieben kann; „Ohne Ordner" nur, wenn dort etwas liegt.
const gruppen = computed<Gruppe[]>(() => {
  const g: Gruppe[] = store.ordnerListe.map((o) => ({
    id: o.id,
    name: o.name,
    chars: store.liste.filter((c) => c.ordner_id === o.id),
  }))
  const ohne = store.liste.filter((c) => c.ordner_id === null)
  if (ohne.length > 0 || !hatOrdner.value) {
    g.push({ id: null, name: 'Ohne Ordner', chars: ohne })
  }
  return g
})

const alleOffen = computed(() => offenePanels.value.length >= gruppen.value.length)

function alleUmschalten() {
  offenePanels.value = alleOffen.value ? [] : gruppen.value.map((g) => g.id ?? 'ohne')
}

async function meldeFehler(fn: () => Promise<void>) {
  try {
    await fn()
  } catch (e) {
    meldung.value = e instanceof ApiError ? e.message : 'Aktion fehlgeschlagen'
    meldungSichtbar.value = true
  }
}

async function importiereDatei(event: Event) {
  const input = event.target as HTMLInputElement
  const datei = input.files?.[0]
  input.value = ''
  if (!datei) return

  // 1) Datei einlesen und als JSON parsen. Ein führendes UTF-8-BOM (bei
  //    Windows-/Alt-Exporten häufig) lässt JSON.parse scheitern → vorher entfernen.
  let daten: unknown
  try {
    const text = (await datei.text()).replace(/^\uFEFF/, '')
    daten = JSON.parse(text)
  } catch {
    meldung.value = 'Import fehlgeschlagen — die Datei ist kein gültiges JSON.'
    meldungSichtbar.value = true
    return
  }

  // 2) An den Server schicken. Backend-Fehlermeldung (z. B. „Kein gültiges
  //    Charakter-JSON") durchreichen, statt sie hinter einem generischen Text zu verstecken.
  try {
    const charakter = await store.importiereCharakter(daten)
    router.push(`/charakter/${charakter.id}`)
  } catch (e) {
    const grund = e instanceof ApiError ? e.message : 'unbekannter Fehler'
    meldung.value = `Import fehlgeschlagen — ${grund}`
    meldungSichtbar.value = true
  }
}

onMounted(async () => {
  await Promise.all([
    store.ladeListe(),
    store.ladeOrdner(),
    store.ladeArchetypen(),
    einstellungenStore.ladeSettings(),
  ])
})

// Archetypen je Setting gruppieren (Reihenfolge wie in der Ordner-Übersicht).
const archetypenNachSetting = computed(() =>
  store.archetypenOrdner.map((o) => ({
    setting: o.setting,
    anzahl: o.anzahl,
    archetypen: store.archetypen.filter((a) => a.setting === o.setting),
  })),
)

const archetypPanels = ref<string[]>([])

async function dupliziere(a: Archetyp) {
  await meldeFehler(async () => {
    const charakter = await store.dupliziereArchetyp(a.id)
    meldung.value = `„${a.name}" wurde in deine Charaktere kopiert.`
    meldungSichtbar.value = true
    router.push(`/charakter/${charakter.id}`)
  })
}

async function erstelleNeuenCharakter() {
  if (!neuerName.value.trim()) return
  const charakter = await store.erstelleCharakter(neuerName.value, neuesSetting.value)
  dialogOffen.value = false
  neuerName.value = ''
  router.push(`/charakter/${charakter.id}`)
}

async function deleteChar(id: number) {
  if (confirm('Charakter wirklich löschen?')) {
    await store.loescheCharakter(id)
  }
}

function ordnerDialogOeffnen(ordner?: Gruppe) {
  ordnerBearbeitenId.value = ordner?.id ?? null
  ordnerName.value = ordner?.name ?? ''
  ordnerDialogOffen.value = true
}

async function speichereOrdner() {
  const name = ordnerName.value.trim()
  if (!name) return
  await meldeFehler(async () => {
    if (ordnerBearbeitenId.value === null) {
      await store.erstelleOrdner(name)
    } else {
      await store.benenneOrdner(ordnerBearbeitenId.value, name)
    }
    ordnerDialogOffen.value = false
  })
}

async function loescheOrdner(ordner: Gruppe) {
  if (ordner.id === null) return
  const anzahl = ordner.chars.length
  const hinweis = anzahl
    ? `\n\nDie ${anzahl} enthaltenen Charaktere bleiben erhalten und landen „ohne Ordner".`
    : ''
  if (confirm(`Ordner „${ordner.name}" löschen?${hinweis}`)) {
    await meldeFehler(() => store.loescheOrdner(ordner.id as number))
  }
}

async function verschiebe(char: CharakterListItem, ordnerId: number | null) {
  await meldeFehler(() => store.verschiebeCharakter(char.id, ordnerId))
}
</script>
