// Gastmodus: Charaktere ohne Konto liegen nur im localStorage dieses Browsers.
// Sie bekommen negative IDs, damit Editor, Routen und Karten unverändert mit
// CharakterDetail arbeiten können — Server-IDs sind immer positiv.
import type { CharakterDaten, CharakterDetail } from '@/types/charakter'

const SCHLUESSEL = 'gast_charaktere'

export function istGastId(id: number): boolean {
  return id < 0
}

function lese(): CharakterDetail[] {
  try {
    const roh = localStorage.getItem(SCHLUESSEL)
    const liste = roh ? JSON.parse(roh) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

function schreibe(liste: CharakterDetail[]) {
  try {
    localStorage.setItem(SCHLUESSEL, JSON.stringify(liste))
  } catch {
    // Speicher voll oder gesperrt (privates Fenster) — der Editor arbeitet weiter
  }
}

export function ladeGastCharaktere(): CharakterDetail[] {
  return lese().sort((a, b) => b.aktualisiert_am.localeCompare(a.aktualisiert_am))
}

export function ladeGastCharakter(id: number): CharakterDetail | null {
  return lese().find((c) => c.id === id) ?? null
}

export function legeGastCharakterAn(daten: CharakterDaten, charName: string): CharakterDetail {
  const liste = lese()
  const jetzt = new Date().toISOString()
  // Kleinste vorhandene ID minus 1 — eindeutig und immer negativ
  const id = Math.min(0, ...liste.map((c) => c.id)) - 1
  const charakter: CharakterDetail = {
    id,
    ordner_id: null,
    char_name: charName || daten.profil_daten?.Name || 'Unbenannt',
    active_setting_name: daten.active_setting_name ?? 'SWAE',
    char_gen_completed: !!daten.char_gen_completed,
    aktualisiert_am: jetzt,
    erstellt_am: jetzt,
    charakter_daten: daten,
  }
  liste.push(charakter)
  schreibe(liste)
  return charakter
}

export function speichereGastCharakter(charakter: CharakterDetail) {
  const liste = lese()
  const eintrag: CharakterDetail = {
    ...JSON.parse(JSON.stringify(charakter)),
    char_name: charakter.charakter_daten.profil_daten?.Name?.trim() || charakter.char_name,
    aktualisiert_am: new Date().toISOString(),
  }
  const index = liste.findIndex((c) => c.id === charakter.id)
  if (index >= 0) liste[index] = eintrag
  else liste.push(eintrag)
  schreibe(liste)
}

export function loescheGastCharakter(id: number) {
  schreibe(lese().filter((c) => c.id !== id))
}
