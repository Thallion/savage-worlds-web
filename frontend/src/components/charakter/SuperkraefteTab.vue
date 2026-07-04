<template>
  <v-card flat>
    <v-card-text>
      <v-alert v-if="!skp?.talent_gewaehlt" type="warning" density="compact" class="mb-4">
        Zuerst im Talente-Tab das Talent <strong>Superkräfte</strong> wählen.
      </v-alert>

      <div class="d-flex ga-4 flex-wrap align-center mb-4">
        <v-select
          :model-value="skp?.stufe"
          :items="stufenItems"
          label="Machtstufe"
          density="compact"
          hide-details
          style="max-width: 340px"
          @update:model-value="(s: string) => ausfuehren('superkraft/stufe', s)"
        />
        <v-alert type="info" density="compact" class="flex-grow-1">
          Superkraftpunkte: <strong>{{ skp?.verbleibend ?? 0 }}</strong> von {{ skp?.budget ?? 0 }}
          frei — Kraftobergrenze {{ skp?.kraftobergrenze ?? 0 }} SKP pro Kraft
        </v-alert>
      </div>

      <v-snackbar v-model="meldungSichtbar" :timeout="4000">{{ meldung }}</v-snackbar>

      <!-- Gewählte Kräfte -->
      <div v-if="gewaehlt.length" class="mb-6">
        <h3 class="text-subtitle-1 mb-2">Gewählte Kräfte</h3>
        <v-card v-for="kraft in gewaehlt" :key="kraft.name" variant="outlined" class="mb-2">
          <v-card-text>
            <div class="d-flex align-center ga-2 flex-wrap">
              <strong>{{ kraft.name }}</strong>
              <span class="text-caption">({{ kraft.gesamt }} SKP)</span>
              <v-btn
                icon="mdi-minus"
                size="x-small"
                variant="text"
                @click="ausfuehren('superkraft/punkte', `${kraft.name}:${kraft.punkte - 1}`)"
              />
              <span>{{ kraft.punkte }} Punkte</span>
              <v-btn
                icon="mdi-plus"
                size="x-small"
                variant="text"
                @click="ausfuehren('superkraft/punkte', `${kraft.name}:${kraft.punkte + 1}`)"
              />
              <v-spacer />
              <v-btn
                icon="mdi-delete"
                size="x-small"
                variant="text"
                @click="ausfuehren('superkraft/entfernen', kraft.name)"
              />
            </div>
            <div class="text-caption text-medium-emphasis mb-2">{{ kraft.beschreibung.slice(0, 160) }}</div>
            <div class="d-flex ga-1 flex-wrap">
              <v-chip
                v-for="mod in kraft.modOptionen"
                :key="mod.name"
                size="small"
                :color="mod.gewaehlt ? 'primary' : undefined"
                :variant="mod.gewaehlt ? 'elevated' : 'outlined'"
                @click="ausfuehren('superkraft/modifikator', `${kraft.name}:${mod.name}`)"
              >
                {{ mod.name }} ({{ mod.kosten }})
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Katalog -->
      <v-text-field
        v-model="suche"
        label="Superkraft suchen..."
        prepend-inner-icon="mdi-magnify"
        clearable
        density="compact"
        hide-details
        class="mb-2"
        style="max-width: 320px"
      />
      <v-table density="compact">
        <thead>
          <tr>
            <th>Kraft</th>
            <th class="text-right">Kosten</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="kraft in katalogGefiltert" :key="kraft.name">
            <td>
              <div>{{ kraft.name }}</div>
              <div class="text-caption text-medium-emphasis">{{ (kraft.beschreibung || '').slice(0, 120) }}</div>
            </td>
            <td class="text-right">{{ kraft.kosten }}</td>
            <td class="text-right">
              <v-btn
                size="small"
                variant="tonal"
                color="primary"
                :disabled="!skp?.talent_gewaehlt"
                @click="ausfuehren('superkraft/waehlen', kraft.name)"
              >
                Wählen
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import { useEinstellungenStore } from '@/stores/einstellungen'

const store = useCharakterStore()
const einstellungenStore = useEinstellungenStore()

const suche = ref('')
const meldung = ref('')
const meldungSichtbar = ref(false)

const daten = computed(() => store.aktuellerCharakter!.charakter_daten)
const skp = computed(() => store.abgeleiteteWerte?.superkraefte ?? null)

const setting = computed<any>(() => einstellungenStore.aktuellesSetting ?? {})
const krafte = computed<Record<string, any>>(() => setting.value.krafte ?? {})

const stufenItems = computed(() =>
  Object.entries(setting.value.machtstufen ?? {}).map(([id, s]: [string, any]) => ({
    value: id,
    title: `${s.name} (${s.superkraftpunkte} SKP)`,
  })),
)

const gewaehlt = computed(() =>
  Object.entries(daten.value.selected_superkraefte ?? {}).map(([name, eintrag]) => {
    const kraft = krafte.value[name] ?? {}
    const mods = eintrag.modifikatoren ?? {}
    // kraftspezifische + generische Modifikatoren anbieten
    const optionen: { name: string; kosten: number | string; gewaehlt: boolean }[] = []
    for (const [modName, mod] of Object.entries<any>({
      ...(setting.value.kraft_modifikatoren ?? {}),
      ...(kraft.modifikatoren ?? {}),
    })) {
      optionen.push({ name: modName, kosten: mod.kosten, gewaehlt: modName in mods })
    }
    const gesamt = eintrag.punkte + Object.values(mods).reduce((a, b) => a + b, 0)
    return {
      name,
      punkte: eintrag.punkte,
      gesamt,
      beschreibung: kraft.beschreibung ?? '',
      modOptionen: optionen,
    }
  }),
)

const katalogGefiltert = computed(() => {
  const s = (suche.value ?? '').toLowerCase()
  const bereits = daten.value.selected_superkraefte ?? {}
  return Object.values(krafte.value)
    .filter(
      (k: any) => k.aktiv !== false && !(k.name in bereits) && (!s || k.name.toLowerCase().includes(s)),
    )
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
})

async function ausfuehren(aktion: string, element?: string) {
  const result = await store.spiellogikAktion(aktion, element)
  if (!result.success && result.message) {
    meldung.value = result.message
    meldungSichtbar.value = true
  }
}
</script>
