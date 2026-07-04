import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'

export interface SettingListItem {
  name: string
  datei: string
  custom: boolean
  beschreibung: string
  statistik: Record<string, number>
}

export interface SettingKonflikt {
  typ: string
  name: string
  quellen: string[]
}

export interface SettingVerwaltungAntwort {
  name: string
  custom: boolean
  beschreibung: string
  statistik: Record<string, number>
  konflikte: SettingKonflikt[]
  warnungen: string[]
}

export interface SettingErstellenPayload {
  name: string
  beschreibung?: string
  modus: 'leer' | 'kopie' | 'zusammenfuehrung' | 'aus_charakter' | 'elementauswahl'
  quellen?: string[]
  charakter_id?: number
  basis?: string
  elemente?: Record<string, Record<string, string[]>>
}

export const useEinstellungenStore = defineStore('einstellungen', () => {
  const verfuegbareSettings = ref<SettingListItem[]>([])
  const aktuellesSetting = ref<Record<string, any> | null>(null)
  const loading = ref(false)
  // Setting-JSONs sind groß — für Detail-Ansicht und Elementauswahl cachen
  const settingCache = new Map<string, Record<string, any>>()

  async function ladeSettings() {
    verfuegbareSettings.value = await api.get<SettingListItem[]>('/settings')
  }

  async function ladeSetting(name: string) {
    loading.value = true
    try {
      aktuellesSetting.value = await holeSetting(name)
    } finally {
      loading.value = false
    }
  }

  async function holeSetting(name: string): Promise<Record<string, any>> {
    const gecacht = settingCache.get(name)
    if (gecacht) return gecacht
    const setting = await api.get<Record<string, any>>(`/settings/${encodeURIComponent(name)}`)
    settingCache.set(name, setting)
    return setting
  }

  function invalidiere(name: string) {
    settingCache.delete(name)
  }

  async function erstelleSetting(payload: SettingErstellenPayload) {
    const antwort = await api.post<SettingVerwaltungAntwort>('/settings', payload)
    await ladeSettings()
    return antwort
  }

  async function aktualisiereSetting(
    name: string,
    body: { neuer_name?: string; beschreibung?: string },
  ) {
    const antwort = await api.put<SettingVerwaltungAntwort>(
      `/settings/${encodeURIComponent(name)}`,
      body,
    )
    invalidiere(name)
    await ladeSettings()
    return antwort
  }

  async function loescheSetting(name: string) {
    await api.delete(`/settings/${encodeURIComponent(name)}`)
    invalidiere(name)
    await ladeSettings()
  }

  async function elementeHinzufuegen(
    name: string,
    quelle: string,
    elemente: Record<string, string[]>,
  ) {
    const antwort = await api.post<SettingVerwaltungAntwort>(
      `/settings/${encodeURIComponent(name)}/elemente`,
      { quelle, elemente },
    )
    invalidiere(name)
    await ladeSettings()
    return antwort
  }

  async function elementEntfernen(name: string, typ: string, elementName: string) {
    const antwort = await api.post<SettingVerwaltungAntwort>(
      `/settings/${encodeURIComponent(name)}/elemente/entfernen`,
      { typ, element_name: elementName },
    )
    invalidiere(name)
    await ladeSettings()
    return antwort
  }

  return {
    verfuegbareSettings,
    aktuellesSetting,
    loading,
    ladeSettings,
    ladeSetting,
    holeSetting,
    invalidiere,
    erstelleSetting,
    aktualisiereSetting,
    loescheSetting,
    elementeHinzufuegen,
    elementEntfernen,
  }
})
