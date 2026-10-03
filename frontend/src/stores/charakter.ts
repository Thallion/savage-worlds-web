import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import {
  istGastId,
  ladeGastCharakter,
  ladeGastCharaktere,
  legeGastCharakterAn,
  loescheGastCharakter,
  speichereGastCharakter,
} from '@/utils/gastCharaktere'
import type {
  AbgeleiteteWerte,
  Archetyp,
  ArchetypOrdner,
  BestiariumEintrag,
  BestiariumKreatur,
  CharakterDaten,
  CharakterDetail,
  CharakterListItem,
  Kampfprofil,
  Ordner,
} from '@/types/charakter'

export const useCharakterStore = defineStore('charakter', () => {
  const liste = ref<CharakterListItem[]>([])
  const ordnerListe = ref<Ordner[]>([])
  const archetypen = ref<Archetyp[]>([])
  const archetypenOrdner = ref<ArchetypOrdner[]>([])
  const bestiarium = ref<BestiariumEintrag[]>([])
  const aktuellerCharakter = ref<CharakterDetail | null>(null)
  const abgeleiteteWerte = ref<AbgeleiteteWerte | null>(null)
  const loading = ref(false)

  // Gastmodus: ohne Anmeldung liegen die Charaktere im Browser (negative IDs)
  const authStore = useAuthStore()
  const istGast = computed(() => !authStore.isLoggedIn)
  const aktuellIstGast = computed(() =>
    aktuellerCharakter.value ? istGastId(aktuellerCharakter.value.id) : false,
  )

  /** Füllt fehlende Felder nach (wie das Lazy-Init beim Laden vom Server). */
  async function normalisiere(daten: unknown) {
    const antwort = await api.post<{ charakter_daten: CharakterDaten }>(
      '/spiellogik/charakter/normalisieren',
      daten,
    )
    return antwort.charakter_daten
  }

  function ladeDateiHerunter(daten: unknown, name: string) {
    const blob = new Blob([JSON.stringify(daten, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name || 'charakter'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ---- Undo/Redo (Original: undo_manager) ----
  // Der gesamte Charakter liegt in einem JSON-Blob und jede Spiellogik-Aktion
  // ersetzt ihn. Daher genügt eine Historie aus Blob-Snapshots: vor jeder
  // erfolgreichen Mutation wird der Zustand davor gemerkt, Undo stellt ihn
  // wieder her, Redo führt ihn erneut aus.
  const MAX_HISTORIE = 50
  const undoStack = ref<CharakterDaten[]>([])
  const redoStack = ref<CharakterDaten[]>([])
  const kannUndo = computed(() => undoStack.value.length > 0)
  const kannRedo = computed(() => redoStack.value.length > 0)

  function klon<T>(wert: T): T {
    return JSON.parse(JSON.stringify(wert)) as T
  }

  function historieZuruecksetzen() {
    undoStack.value = []
    redoStack.value = []
  }

  /** Merkt den Zustand vor einer Mutation und verwirft die Redo-Kette. */
  function merkeSchritt(vorher: CharakterDaten) {
    undoStack.value.push(vorher)
    if (undoStack.value.length > MAX_HISTORIE) undoStack.value.shift()
    redoStack.value = []
  }

  /** Setzt den Blob und synchronisiert die davon abgeleiteten Zeilen-Spalten. */
  function wendeDatenAn(daten: CharakterDaten) {
    const char = aktuellerCharakter.value
    if (!char) return
    char.charakter_daten = daten
    char.active_setting_name = daten.active_setting_name ?? char.active_setting_name
    char.char_gen_completed = daten.char_gen_completed ?? char.char_gen_completed
    const name = daten.profil_daten?.Name
    if (name) char.char_name = name
  }

  async function undo() {
    if (!aktuellerCharakter.value || undoStack.value.length === 0) return
    redoStack.value.push(klon(aktuellerCharakter.value.charakter_daten))
    wendeDatenAn(undoStack.value.pop()!)
    await berechneWerte()
  }

  async function redo() {
    if (!aktuellerCharakter.value || redoStack.value.length === 0) return
    undoStack.value.push(klon(aktuellerCharakter.value.charakter_daten))
    wendeDatenAn(redoStack.value.pop()!)
    await berechneWerte()
  }

  async function ladeListe() {
    loading.value = true
    try {
      liste.value = istGast.value
        ? ladeGastCharaktere()
        : await api.get<CharakterListItem[]>('/charaktere')
    } finally {
      loading.value = false
    }
  }

  async function ladeCharakter(id: number) {
    loading.value = true
    try {
      if (istGastId(id)) {
        const gast = ladeGastCharakter(id)
        if (!gast) throw new Error('Charakter nicht gefunden')
        gast.charakter_daten = await normalisiere(gast.charakter_daten)
        aktuellerCharakter.value = gast
      } else {
        aktuellerCharakter.value = await api.get<CharakterDetail>(`/charaktere/${id}`)
      }
      historieZuruecksetzen()
      await berechneWerte()
    } finally {
      loading.value = false
    }
  }

  async function berechneWerte() {
    if (!aktuellerCharakter.value) return
    abgeleiteteWerte.value = await api.post<AbgeleiteteWerte>('/spiellogik/berechne', {
      charakter_daten: aktuellerCharakter.value.charakter_daten,
    })
  }

  async function erstelleCharakter(charName: string, settingName: string) {
    if (istGast.value) {
      const { charakter_daten } = await api.post<{ charakter_daten: CharakterDaten }>(
        '/spiellogik/charakter/neu',
        { char_name: charName, active_setting_name: settingName },
      )
      const charakter = legeGastCharakterAn(charakter_daten, charName)
      await ladeListe()
      return charakter
    }
    const charakter = await api.post<CharakterDetail>('/charaktere', {
      char_name: charName,
      active_setting_name: settingName,
    })
    await ladeListe()
    return charakter
  }

  async function speichereCharakter() {
    if (!aktuellerCharakter.value) return
    const id = aktuellerCharakter.value.id
    if (istGastId(id)) {
      speichereGastCharakter(aktuellerCharakter.value)
      const name = aktuellerCharakter.value.charakter_daten.profil_daten?.Name?.trim()
      if (name) aktuellerCharakter.value.char_name = name
      return
    }
    const gespeichert = await api.put<CharakterDetail>(`/charaktere/${id}`, {
      char_name: aktuellerCharakter.value.char_name,
      active_setting_name: aktuellerCharakter.value.active_setting_name,
      char_gen_completed: aktuellerCharakter.value.char_gen_completed,
      charakter_daten: aktuellerCharakter.value.charakter_daten,
    })
    // Der Server leitet char_name aus dem Profilnamen ab (und nummeriert bei
    // Namensgleichheit) — den Stand übernehmen, damit Kopfzeile und Export folgen.
    aktuellerCharakter.value.char_name = gespeichert.char_name
  }

  async function loescheCharakter(id: number) {
    if (istGastId(id)) {
      loescheGastCharakter(id)
      await ladeListe()
      return
    }
    await api.delete(`/charaktere/${id}`)
    await ladeListe()
  }

  async function exportiereCharakter(id: number, name: string) {
    const daten = istGastId(id)
      ? ladeGastCharakter(id)?.charakter_daten
      : await api.get<CharakterDaten>(`/charaktere/${id}/export`)
    if (daten) ladeDateiHerunter(daten, name)
  }

  async function importiereCharakter(daten: unknown) {
    if (istGast.value) {
      const normalisiert = await normalisiere(daten)
      const charakter = legeGastCharakterAn(
        normalisiert,
        normalisiert.profil_daten?.Name?.trim() || 'Importierter Charakter',
      )
      await ladeListe()
      return charakter
    }
    const charakter = await api.post<CharakterDetail>('/charaktere/import', daten)
    await ladeListe()
    return charakter
  }

  // ---- Ordner ----

  /**
   * Übernimmt nach der Anmeldung die Gast-Charaktere aus dem Browser ins Konto.
   * Erfolgreich importierte werden lokal gelöscht; gibt die Anzahl zurück.
   */
  async function uebernehmeGastCharaktere(): Promise<number> {
    let anzahl = 0
    for (const gast of ladeGastCharaktere()) {
      try {
        await api.post<CharakterDetail>('/charaktere/import', gast.charakter_daten)
        loescheGastCharakter(gast.id)
        anzahl++
      } catch {
        // bleibt im Browser und wird beim nächsten Login erneut versucht
      }
    }
    return anzahl
  }

  async function ladeOrdner() {
    if (istGast.value) {
      ordnerListe.value = []
      return
    }
    ordnerListe.value = await api.get<Ordner[]>('/ordner')
  }

  async function erstelleOrdner(name: string) {
    const ordner = await api.post<Ordner>('/ordner', { name })
    await ladeOrdner()
    return ordner
  }

  async function benenneOrdner(id: number, name: string) {
    await api.put(`/ordner/${id}`, { name })
    await ladeOrdner()
  }

  async function loescheOrdner(id: number) {
    await api.delete(`/ordner/${id}`)
    // Charaktere bleiben erhalten (landen „ohne Ordner"), daher beides neu laden.
    await Promise.all([ladeListe(), ladeOrdner()])
  }

  async function verschiebeCharakter(charakterId: number, ordnerId: number | null) {
    await api.put(`/charaktere/${charakterId}/verschieben`, { ordner_id: ordnerId })
    await Promise.all([ladeListe(), ladeOrdner()])
  }

  // ---- Kampfsimulator ----
  // Lädt nur das Kampfprofil; der im Editor geöffnete Charakter bleibt unberührt.

  async function ladeKampfprofil(daten: CharakterDaten) {
    return api.post<Kampfprofil>('/spiellogik/kampfprofil', { charakter_daten: daten })
  }

  async function ladeKampfprofilCharakter(id: number) {
    if (istGastId(id)) {
      const gast = ladeGastCharakter(id)
      if (!gast) throw new Error('Charakter nicht gefunden')
      return ladeKampfprofil(await normalisiere(gast.charakter_daten))
    }
    const charakter = await api.get<CharakterDetail>(`/charaktere/${id}`)
    return ladeKampfprofil(charakter.charakter_daten)
  }

  async function ladeKampfprofilArchetyp(id: string) {
    const daten = await api.get<CharakterDaten>(`/archetypen/${encodeURIComponent(id)}`)
    return ladeKampfprofil(daten)
  }

  // Kreaturen bringen ihre Kampfwerte fertig mit (Parade/Robustheit stehen im
  // Buch), deshalb kommt das Profil direkt vom Bestiarium statt aus /berechne.
  async function ladeKampfprofilKreatur(id: string) {
    return api.get<Kampfprofil>(`/bestiarium/${encodeURIComponent(id)}/kampfprofil`)
  }

  // ---- Bestiarium (schreibgeschützte Kreaturen-Bibliothek) ----

  async function ladeBestiarium() {
    bestiarium.value = await api.get<BestiariumEintrag[]>('/bestiarium')
  }

  async function ladeKreatur(id: string) {
    return api.get<BestiariumKreatur>(`/bestiarium/${encodeURIComponent(id)}`)
  }

  // ---- Archetypen (schreibgeschützte Bibliothek) ----

  async function ladeArchetypen() {
    const [alle, ordner] = await Promise.all([
      api.get<Archetyp[]>('/archetypen'),
      api.get<ArchetypOrdner[]>('/archetypen/ordner'),
    ])
    archetypen.value = alle
    archetypenOrdner.value = ordner
  }

  async function dupliziereArchetyp(id: string, ordnerId: number | null = null) {
    if (istGast.value) {
      const daten = await api.get<CharakterDaten>(`/archetypen/${encodeURIComponent(id)}`)
      return importiereCharakter(daten)
    }
    const charakter = await api.post<CharakterDetail>(
      `/archetypen/${encodeURIComponent(id)}/duplizieren`,
      { ordner_id: ordnerId },
    )
    await Promise.all([ladeListe(), ladeOrdner()])
    return charakter
  }

  async function spiellogikAktion(
    aktion: string,
    elementName?: string,
    ignorierePruefungen = false,
    extra?: Record<string, unknown>,
  ): Promise<{ success: boolean; message: string; bestaetigung_moeglich?: boolean }> {
    if (!aktuellerCharakter.value) return { success: false, message: 'Kein Charakter geladen' }

    const vorher = klon(aktuellerCharakter.value.charakter_daten)
    const result = await api.post<{
      success: boolean
      message: string
      charakter_daten?: CharakterDaten
      bestaetigung_moeglich?: boolean
    }>(`/spiellogik/${aktion}`, {
      charakter_daten: aktuellerCharakter.value.charakter_daten,
      element_name: elementName,
      ignoriere_pruefungen: ignorierePruefungen,
      ...extra,
    })

    if (result.success && result.charakter_daten) {
      merkeSchritt(vorher)
      aktuellerCharakter.value.charakter_daten = result.charakter_daten
      await berechneWerte()
    }
    return result
  }

  async function elementAktion(
    pfad: 'speichern' | 'loeschen',
    body: Record<string, unknown>,
  ): Promise<{ success: boolean; message: string }> {
    if (!aktuellerCharakter.value) return { success: false, message: 'Kein Charakter geladen' }
    const vorher = klon(aktuellerCharakter.value.charakter_daten)
    const result = await api.post<{
      success: boolean
      message: string
      charakter_daten?: CharakterDaten
    }>(`/spiellogik/element/${pfad}`, {
      charakter_daten: aktuellerCharakter.value.charakter_daten,
      ...body,
    })
    if (result.success && result.charakter_daten) {
      merkeSchritt(vorher)
      aktuellerCharakter.value.charakter_daten = result.charakter_daten
      await berechneWerte()
    }
    return result
  }

  function elementSpeichern(
    typ: string,
    name: string,
    elementDaten: Record<string, unknown>,
    alterName?: string,
  ) {
    return elementAktion('speichern', {
      element_typ: typ,
      element_name: name,
      element_daten: elementDaten,
      alter_name: alterName ?? null,
    })
  }

  function elementLoeschen(typ: string, name: string) {
    return elementAktion('loeschen', { element_typ: typ, element_name: name })
  }

  return {
    liste,
    ordnerListe,
    archetypen,
    archetypenOrdner,
    aktuellerCharakter,
    abgeleiteteWerte,
    loading,
    istGast,
    aktuellIstGast,
    kannUndo,
    kannRedo,
    undo,
    redo,
    historieZuruecksetzen,
    ladeListe,
    ladeCharakter,
    berechneWerte,
    erstelleCharakter,
    speichereCharakter,
    loescheCharakter,
    exportiereCharakter,
    importiereCharakter,
    uebernehmeGastCharaktere,
    ladeOrdner,
    erstelleOrdner,
    benenneOrdner,
    loescheOrdner,
    verschiebeCharakter,
    ladeKampfprofilCharakter,
    ladeKampfprofilArchetyp,
    ladeKampfprofilKreatur,
    bestiarium,
    ladeBestiarium,
    ladeKreatur,
    ladeArchetypen,
    dupliziereArchetyp,
    spiellogikAktion,
    elementSpeichern,
    elementLoeschen,
  }
})
