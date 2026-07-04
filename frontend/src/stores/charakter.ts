import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { AbgeleiteteWerte, CharakterDaten, CharakterDetail, CharakterListItem } from '@/types/charakter'

export const useCharakterStore = defineStore('charakter', () => {
  const liste = ref<CharakterListItem[]>([])
  const aktuellerCharakter = ref<CharakterDetail | null>(null)
  const abgeleiteteWerte = ref<AbgeleiteteWerte | null>(null)
  const loading = ref(false)

  async function ladeListe() {
    loading.value = true
    try {
      liste.value = await api.get<CharakterListItem[]>('/charaktere')
    } finally {
      loading.value = false
    }
  }

  async function ladeCharakter(id: number) {
    loading.value = true
    try {
      aktuellerCharakter.value = await api.get<CharakterDetail>(`/charaktere/${id}`)
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
    await api.put(`/charaktere/${id}`, {
      char_name: aktuellerCharakter.value.char_name,
      active_setting_name: aktuellerCharakter.value.active_setting_name,
      char_gen_completed: aktuellerCharakter.value.char_gen_completed,
      charakter_daten: aktuellerCharakter.value.charakter_daten,
    })
  }

  async function loescheCharakter(id: number) {
    await api.delete(`/charaktere/${id}`)
    await ladeListe()
  }

  async function exportiereCharakter(id: number, name: string) {
    const daten = await api.get<CharakterDaten>(`/charaktere/${id}/export`)
    const blob = new Blob([JSON.stringify(daten, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name || 'charakter'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function importiereCharakter(daten: unknown) {
    const charakter = await api.post<CharakterDetail>('/charaktere/import', daten)
    await ladeListe()
    return charakter
  }

  async function spiellogikAktion(
    aktion: string,
    elementName?: string,
    ignorierePruefungen = false,
  ): Promise<{ success: boolean; message: string; bestaetigung_moeglich?: boolean }> {
    if (!aktuellerCharakter.value) return { success: false, message: 'Kein Charakter geladen' }

    const result = await api.post<{
      success: boolean
      message: string
      charakter_daten?: CharakterDaten
      bestaetigung_moeglich?: boolean
    }>(`/spiellogik/${aktion}`, {
      charakter_daten: aktuellerCharakter.value.charakter_daten,
      element_name: elementName,
      ignoriere_pruefungen: ignorierePruefungen,
    })

    if (result.success && result.charakter_daten) {
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
    const result = await api.post<{
      success: boolean
      message: string
      charakter_daten?: CharakterDaten
    }>(`/spiellogik/element/${pfad}`, {
      charakter_daten: aktuellerCharakter.value.charakter_daten,
      ...body,
    })
    if (result.success && result.charakter_daten) {
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
    aktuellerCharakter,
    abgeleiteteWerte,
    loading,
    ladeListe,
    ladeCharakter,
    berechneWerte,
    erstelleCharakter,
    speichereCharakter,
    loescheCharakter,
    exportiereCharakter,
    importiereCharakter,
    spiellogikAktion,
    elementSpeichern,
    elementLoeschen,
  }
})
