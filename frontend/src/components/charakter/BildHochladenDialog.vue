<template>
  <v-dialog :model-value="modelValue" max-width="640" @update:model-value="schliessen">
    <v-card>
      <v-card-title>{{ bestehendesBild ? 'Porträt bearbeiten' : 'Porträt hochladen' }}</v-card-title>

      <v-card-text>
        <!-- Schritt 1: Quelle wählen -->
        <div
          v-if="!bildQuelle"
          class="dropzone"
          :class="{ aktiv: ziehtDrueber }"
          @dragover.prevent="ziehtDrueber = true"
          @dragleave="ziehtDrueber = false"
          @drop.prevent="beimDrop"
          @click="dateiInput?.click()"
        >
          <v-icon size="48" class="mb-2">mdi-image-plus</v-icon>
          <div>Bild hierher ziehen, klicken oder mit Strg+V einfügen</div>
          <div class="text-caption text-medium-emphasis mt-1">
            JPEG, PNG, WebP oder GIF · mindestens {{ BILD_MIN_BREITE }} × {{ BILD_MIN_HOEHE }} Pixel
          </div>
        </div>
        <input
          ref="dateiInput"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          hidden
          @change="beimDateiAuswaehlen"
        />

        <!-- Schritt 2: Zuschneiden (3:4) und Avatar-Ausschnitt -->
        <div v-if="bildQuelle" class="d-flex flex-wrap ga-4 justify-center">
          <div>
            <div
              ref="buehne"
              class="buehne"
              :style="{ width: `${RAHMEN_B}px`, height: `${RAHMEN_H}px` }"
              @pointerdown="zeigerRunter"
              @pointermove="zeigerBewegt"
              @pointerup="zeigerHoch"
              @pointercancel="zeigerHoch"
              @wheel.prevent="beimMausrad"
            >
              <img
                :src="bildQuelle"
                alt=""
                draggable="false"
                :style="{
                  width: `${natB * massstab}px`,
                  height: `${natH * massstab}px`,
                  transform: `translate(${pos.x}px, ${pos.y}px)`,
                }"
              />
              <div
                class="avatar-rahmen"
                :style="{ top: `${fokusY * (RAHMEN_H - RAHMEN_B)}px`, height: `${RAHMEN_B}px` }"
              />
            </div>
            <v-slider
              :model-value="zoom"
              :min="1"
              :max="4"
              :step="0.01"
              prepend-icon="mdi-magnify-minus-outline"
              append-icon="mdi-magnify-plus-outline"
              hide-details
              class="mt-2"
              :style="{ width: `${RAHMEN_B}px` }"
              @update:model-value="setzeZoom"
            />
          </div>

          <div class="d-flex flex-column align-center ga-3 vorschau-spalte">
            <div class="text-caption text-medium-emphasis">Vorschau</div>
            <canvas ref="vorschauKarte" width="72" height="96" class="vorschau-karte" />
            <canvas ref="vorschauAvatar" width="64" height="64" class="vorschau-avatar" />
            <div class="text-caption text-center">Avatar-Ausschnitt<br />(Kreis hoch/runter)</div>
            <v-slider
              v-model="fokusY"
              :min="0"
              :max="1"
              :step="0.01"
              hide-details
              density="compact"
              style="width: 110px; flex: none"
            />
          </div>
        </div>

        <v-alert v-if="fehler" type="error" variant="tonal" density="compact" class="mt-3">
          {{ fehler }}
        </v-alert>
        <v-alert v-else-if="zuKlein" type="warning" variant="tonal" density="compact" class="mt-3">
          Der Ausschnitt ist zu klein ({{ Math.round(quellRechteck.sw) }} Pixel breit, mindestens
          {{ BILD_MIN_BREITE }}). Bitte weniger zoomen oder ein größeres Bild wählen.
        </v-alert>
        <div class="text-caption text-medium-emphasis mt-3">
          Das Porträt wird sofort gespeichert, unabhängig vom „Speichern“ des Charakters. Lade nur
          Bilder hoch, an denen du die Rechte hast. Metadaten (z. B. GPS) werden entfernt.
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn v-if="bildQuelle" variant="text" prepend-icon="mdi-image-refresh" @click="dateiInput?.click()">
          Anderes Bild
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="schliessen(false)">Abbrechen</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="!bildQuelle || zuKlein"
          :loading="speichert"
          @click="speichern"
        >
          Übernehmen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useCharakterStore } from '@/stores/charakter'
import {
  BILD_MIN_BREITE,
  BILD_MIN_HOEHE,
  STANDARD_FOKUS_Y,
  bildUrl,
} from '@/utils/charakterBild'

const props = defineProps<{
  modelValue: boolean
  charakterId: number
  // Vorhandenes Porträt („Ausschnitt ändern“) oder eine per Drag & Drop übergebene Datei
  bestehendesBild?: string | null
  bestehenderFokus?: number | null
  datei?: File | null
}>()

const emit = defineEmits<{ 'update:modelValue': [offen: boolean]; gespeichert: [] }>()

const store = useCharakterStore()

const RAHMEN_B = 270
const RAHMEN_H = 360
const MAX_AUSGABE_B = 1200
const MAX_ROH_MB = 20
const ERLAUBTE_TYPEN = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

const dateiInput = ref<HTMLInputElement>()
const buehne = ref<HTMLDivElement>()
const vorschauKarte = ref<HTMLCanvasElement>()
const vorschauAvatar = ref<HTMLCanvasElement>()

const bildQuelle = ref<string | null>(null)
const bildElement = ref<HTMLImageElement | null>(null)
let objektUrl: string | null = null
const natB = ref(0)
const natH = ref(0)
const zoom = ref(1)
const pos = reactive({ x: 0, y: 0 })
const fokusY = ref(STANDARD_FOKUS_Y)
const fehler = ref('')
const speichert = ref(false)
const ziehtDrueber = ref(false)
// Bei „Ausschnitt ändern“: wurde nur der Avatar-Fokus bewegt, reicht ein PATCH
const zuschnittGeaendert = ref(false)

// Bild deckt den Rahmen bei zoom 1 genau ab (cover)
const grundMassstab = computed(() =>
  natB.value ? Math.max(RAHMEN_B / natB.value, RAHMEN_H / natH.value) : 1,
)
const massstab = computed(() => grundMassstab.value * zoom.value)

/** Sichtbarer Ausschnitt in Original-Pixeln. */
const quellRechteck = computed(() => ({
  sx: -pos.x / massstab.value,
  sy: -pos.y / massstab.value,
  sw: RAHMEN_B / massstab.value,
  sh: RAHMEN_H / massstab.value,
}))
const zuKlein = computed(() => !!bildQuelle.value && quellRechteck.value.sw < BILD_MIN_BREITE - 0.5)

function begrenze() {
  const b = natB.value * massstab.value
  const h = natH.value * massstab.value
  pos.x = Math.min(0, Math.max(RAHMEN_B - b, pos.x))
  pos.y = Math.min(0, Math.max(RAHMEN_H - h, pos.y))
}

function zentriere() {
  pos.x = (RAHMEN_B - natB.value * massstab.value) / 2
  pos.y = (RAHMEN_H - natH.value * massstab.value) / 2
}

// ---- Laden ----

function raeumeObjektUrlAuf() {
  if (objektUrl) URL.revokeObjectURL(objektUrl)
  objektUrl = null
}

async function ladeQuelle(url: string, istBestehend: boolean) {
  fehler.value = ''
  const img = new Image()
  img.decoding = 'async'
  img.src = url
  try {
    await img.decode()
  } catch {
    fehler.value = 'Das Bild konnte nicht gelesen werden.'
    return
  }
  if (img.naturalWidth < BILD_MIN_BREITE || img.naturalHeight < BILD_MIN_HOEHE) {
    fehler.value = `Bild zu klein (mindestens ${BILD_MIN_BREITE} × ${BILD_MIN_HOEHE} Pixel).`
    return
  }
  bildElement.value = img
  natB.value = img.naturalWidth
  natH.value = img.naturalHeight
  zoom.value = 1
  zentriere()
  bildQuelle.value = url
  zuschnittGeaendert.value = !istBestehend
  fokusY.value = istBestehend ? (props.bestehenderFokus ?? STANDARD_FOKUS_Y) : STANDARD_FOKUS_Y
  await nextTick()
  zeichneVorschau()
}

function ladeDatei(datei: File) {
  if (!ERLAUBTE_TYPEN.includes(datei.type)) {
    fehler.value = 'Format nicht unterstützt — erlaubt sind JPEG, PNG, WebP und GIF.'
    return
  }
  if (datei.size > MAX_ROH_MB * 1024 * 1024) {
    fehler.value = `Datei zu groß (max. ${MAX_ROH_MB} MB).`
    return
  }
  raeumeObjektUrlAuf()
  objektUrl = URL.createObjectURL(datei)
  ladeQuelle(objektUrl, false)
}

function beimDateiAuswaehlen(e: Event) {
  const input = e.target as HTMLInputElement
  const datei = input.files?.[0]
  if (datei) ladeDatei(datei)
  input.value = ''
}

function beimDrop(e: DragEvent) {
  ziehtDrueber.value = false
  const datei = e.dataTransfer?.files?.[0]
  if (datei) ladeDatei(datei)
}

function beimEinfuegen(e: ClipboardEvent) {
  const datei = Array.from(e.clipboardData?.files ?? []).find((f) => f.type.startsWith('image/'))
  if (datei) {
    e.preventDefault()
    ladeDatei(datei)
  }
}

watch(
  () => props.modelValue,
  (offen) => {
    if (offen) {
      window.addEventListener('paste', beimEinfuegen)
      zuruecksetzen()
      if (props.datei) ladeDatei(props.datei)
      else if (props.bestehendesBild) ladeQuelle(bildUrl(props.bestehendesBild, 'gross')!, true)
    } else {
      window.removeEventListener('paste', beimEinfuegen)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('paste', beimEinfuegen)
  raeumeObjektUrlAuf()
})

function zuruecksetzen() {
  raeumeObjektUrlAuf()
  bildQuelle.value = null
  bildElement.value = null
  fehler.value = ''
  speichert.value = false
}

// ---- Verschieben & Zoomen (Maus, Touch, Pinch) ----

const zeiger = new Map<number, { x: number; y: number }>()
let pinchAbstand = 0

function abstand() {
  const [a, b] = [...zeiger.values()]
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function zeigerRunter(e: PointerEvent) {
  buehne.value?.setPointerCapture(e.pointerId)
  zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY })
  if (zeiger.size === 2) pinchAbstand = abstand()
}

function zeigerBewegt(e: PointerEvent) {
  const vorher = zeiger.get(e.pointerId)
  if (!vorher) return
  if (zeiger.size === 1) {
    pos.x += e.clientX - vorher.x
    pos.y += e.clientY - vorher.y
    begrenze()
    zuschnittGeaendert.value = true
  }
  zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY })
  if (zeiger.size === 2 && pinchAbstand) {
    const neu = abstand()
    setzeZoom(zoom.value * (neu / pinchAbstand))
    pinchAbstand = neu
  }
}

function zeigerHoch(e: PointerEvent) {
  zeiger.delete(e.pointerId)
  pinchAbstand = 0
}

function beimMausrad(e: WheelEvent) {
  setzeZoom(zoom.value * (e.deltaY < 0 ? 1.08 : 1 / 1.08))
}

/** Zoomt um die Rahmenmitte, damit der Bildausschnitt nicht wegspringt. */
function setzeZoom(neu: number) {
  const mitteX = (RAHMEN_B / 2 - pos.x) / massstab.value
  const mitteY = (RAHMEN_H / 2 - pos.y) / massstab.value
  zoom.value = Math.min(4, Math.max(1, neu))
  pos.x = RAHMEN_B / 2 - mitteX * massstab.value
  pos.y = RAHMEN_H / 2 - mitteY * massstab.value
  begrenze()
  zuschnittGeaendert.value = true
}

// ---- Vorschau & Ausgabe ----

function zeichne(canvas: HTMLCanvasElement, avatar: boolean) {
  const img = bildElement.value
  const ctx = canvas.getContext('2d')
  if (!img || !ctx) return
  const { sx, sy, sw, sh } = quellRechteck.value
  ctx.imageSmoothingQuality = 'high'
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  if (avatar) {
    ctx.drawImage(img, sx, sy + fokusY.value * (sh - sw), sw, sw, 0, 0, canvas.width, canvas.height)
  } else {
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
  }
}

function zeichneVorschau() {
  if (vorschauKarte.value) zeichne(vorschauKarte.value, false)
  if (vorschauAvatar.value) zeichne(vorschauAvatar.value, true)
}

watch([() => pos.x, () => pos.y, zoom, fokusY], () => requestAnimationFrame(zeichneVorschau))

function alsBlob(canvas: HTMLCanvasElement, typ: string, qualitaet: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, typ, qualitaet))
}

/** Ausschnitt im Browser auf max. 1200 × 1600 bringen — spart Upload und Server-CPU. */
async function erzeugeAusschnitt(): Promise<Blob> {
  const breite = Math.min(MAX_AUSGABE_B, Math.round(quellRechteck.value.sw))
  const canvas = document.createElement('canvas')
  canvas.width = breite
  canvas.height = Math.round((breite * 4) / 3)
  zeichne(canvas, false)
  // Ältere Safaris können kein WebP kodieren und liefern stattdessen PNG
  const webp = await alsBlob(canvas, 'image/webp', 0.9)
  if (webp?.type === 'image/webp') return webp
  const jpeg = await alsBlob(canvas, 'image/jpeg', 0.9)
  if (!jpeg) throw new Error('Bild konnte nicht erzeugt werden')
  return jpeg
}

async function speichern() {
  speichert.value = true
  fehler.value = ''
  try {
    if (props.bestehendesBild && !zuschnittGeaendert.value) {
      await store.setzeBildFokus(props.charakterId, fokusY.value)
    } else {
      await store.ladeBildHoch(props.charakterId, await erzeugeAusschnitt(), fokusY.value)
    }
    emit('gespeichert')
    schliessen(false)
  } catch (e) {
    fehler.value = e instanceof Error ? e.message : 'Hochladen fehlgeschlagen.'
  } finally {
    speichert.value = false
  }
}

function schliessen(offen: boolean) {
  if (!offen) {
    zuruecksetzen()
    emit('update:modelValue', false)
  }
}
</script>

<style scoped>
.dropzone {
  border: 2px dashed rgba(var(--v-theme-on-surface), 0.3);
  border-radius: 8px;
  padding: 40px 16px;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.15s;
}
.dropzone:hover,
.dropzone.aktiv {
  background-color: rgba(var(--v-theme-primary), 0.08);
  border-color: rgb(var(--v-theme-primary));
}
.buehne {
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background-color: #222;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.buehne:active {
  cursor: grabbing;
}
.buehne img {
  position: absolute;
  top: 0;
  left: 0;
  max-width: none;
  transform-origin: 0 0;
  pointer-events: none;
}
.avatar-rahmen {
  position: absolute;
  left: 0;
  right: 0;
  border: 2px dashed rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4);
  border-radius: 50%;
  pointer-events: none;
}
.vorschau-spalte {
  width: 120px;
}
.vorschau-karte {
  border-radius: 6px;
}
.vorschau-avatar {
  border-radius: 50%;
}
</style>
