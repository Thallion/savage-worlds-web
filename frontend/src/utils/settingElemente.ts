// Bearbeitung von Setting-Elementen (Spiegel von backend/app/services/setting_elemente.py).
// Charakter-Overrides (eigene/bearbeitete/gelöschte Elemente) liegen in
// charakter_daten.setting_overrides und werden hier über den Setting-Katalog gemischt.

export type ElementTyp = 'talente' | 'handicaps' | 'maechte' | 'ausruestung'

export function mergeKatalog(
  basis: Record<string, any> | undefined | null,
  charakterDaten: any,
  typ: ElementTyp,
): Record<string, any> {
  const overrides = charakterDaten?.setting_overrides ?? {}
  const eigene = overrides[typ] ?? {}
  const geloescht: string[] = overrides.geloescht?.[typ] ?? []
  const result: Record<string, any> = { ...(basis ?? {}), ...eigene }
  for (const name of geloescht) delete result[name]
  return result
}

export interface Feld {
  key: string
  label: string
  typ: 'text' | 'textarea' | 'int' | 'float' | 'select'
  optionen?: string[]
  // nur bei ausruestung: Feld gilt nur für diese Kategorien
  nurKategorie?: string[]
  // Waffen-Eigenschaften liegen verschachtelt in element.eigenschaften
  eigenschaft?: boolean
}

const RANG_OPTIONEN = ['A', 'F', 'V', 'H', 'L']

// Formularfelder je Element-Typ (angelehnt an die FELDER der Original-Popups)
export const FELDER: Record<ElementTyp, Feld[]> = {
  talente: [
    { key: 'kategorie', label: 'Kategorie', typ: 'text' },
    { key: 'rang', label: 'Rang', typ: 'select', optionen: RANG_OPTIONEN },
    { key: 'beschreibung', label: 'Beschreibung', typ: 'textarea' },
    { key: 'voraussetzungen', label: 'Voraussetzungen (durch Komma getrennt)', typ: 'text' },
    { key: 'neue_maechte', label: 'Neue Mächte', typ: 'int' },
    { key: 'machtpunkte', label: 'Machtpunkte', typ: 'int' },
  ],
  handicaps: [
    { key: 'stufe', label: 'Stufe', typ: 'select', optionen: ['leicht', 'schwer'] },
    { key: 'beschreibung', label: 'Beschreibung', typ: 'textarea' },
  ],
  maechte: [
    { key: 'rang', label: 'Rang', typ: 'select', optionen: RANG_OPTIONEN },
    { key: 'machtpunkte', label: 'Machtpunkte', typ: 'int' },
    { key: 'reichweite', label: 'Reichweite', typ: 'text' },
    { key: 'dauer', label: 'Dauer', typ: 'text' },
    { key: 'beschreibung', label: 'Beschreibung', typ: 'textarea' },
    { key: 'voraussetzungen', label: 'Voraussetzungen (durch Komma getrennt)', typ: 'text' },
  ],
  ausruestung: [
    { key: 'kategorie', label: 'Kategorie', typ: 'select', optionen: ['Allgemein', 'Waffe', 'Rüstung', 'Schild'] },
    { key: 'kosten', label: 'Kosten', typ: 'float' },
    { key: 'gewicht', label: 'Gewicht (kg)', typ: 'float' },
    { key: 'beschreibung', label: 'Beschreibung', typ: 'textarea' },
    { key: 'mindeststaerke', label: 'Mindeststärke (z. B. W6)', typ: 'text', nurKategorie: ['Waffe', 'Rüstung', 'Schild'] },
    { key: 'Schaden', label: 'Schaden (z. B. Stä+W6)', typ: 'text', nurKategorie: ['Waffe'], eigenschaft: true },
    { key: 'Reichweite', label: 'Reichweite', typ: 'text', nurKategorie: ['Waffe'], eigenschaft: true },
    { key: 'FR', label: 'Feuerrate', typ: 'text', nurKategorie: ['Waffe'], eigenschaft: true },
    { key: 'Schuss', label: 'Schuss', typ: 'text', nurKategorie: ['Waffe'], eigenschaft: true },
    { key: 'PB', label: 'Panzerbrechend', typ: 'text', nurKategorie: ['Waffe'], eigenschaft: true },
    { key: 'torso', label: 'Panzerung Torso', typ: 'int', nurKategorie: ['Rüstung'] },
    { key: 'arme', label: 'Panzerung Arme', typ: 'int', nurKategorie: ['Rüstung'] },
    { key: 'beine', label: 'Panzerung Beine', typ: 'int', nurKategorie: ['Rüstung'] },
    { key: 'kopf', label: 'Panzerung Kopf', typ: 'int', nurKategorie: ['Rüstung'] },
    { key: 'parade', label: 'Parade-Bonus', typ: 'int', nurKategorie: ['Schild'] },
    { key: 'deckung', label: 'Deckung', typ: 'int', nurKategorie: ['Schild'] },
  ],
}

export const TYP_LABEL: Record<ElementTyp, string> = {
  talente: 'Talent',
  handicaps: 'Handicap',
  maechte: 'Macht',
  ausruestung: 'Ausrüstung',
}

/** Formularwerte aus einem bestehenden Element befüllen. */
export function elementZuFormular(typ: ElementTyp, element: Record<string, any>): Record<string, any> {
  const werte: Record<string, any> = {}
  for (const feld of FELDER[typ]) {
    let wert = feld.eigenschaft ? element.eigenschaften?.[feld.key] : element[feld.key]
    if (feld.key === 'voraussetzungen' && Array.isArray(wert)) wert = wert.join(', ')
    werte[feld.key] = wert ?? (feld.typ === 'int' || feld.typ === 'float' ? 0 : '')
  }
  return werte
}

/** Formularwerte in element_daten fürs Backend umwandeln. */
export function formularZuElement(typ: ElementTyp, werte: Record<string, any>): Record<string, any> {
  const element: Record<string, any> = {}
  const eigenschaften: Record<string, any> = {}
  const kategorie = werte.kategorie
  for (const feld of FELDER[typ]) {
    if (feld.nurKategorie && !feld.nurKategorie.includes(kategorie)) continue
    let wert = werte[feld.key]
    if (feld.typ === 'int') wert = parseInt(wert) || 0
    if (feld.typ === 'float') wert = parseFloat(wert) || 0
    if (feld.eigenschaft) {
      eigenschaften[feld.key] = wert || '-'
    } else {
      element[feld.key] = wert
    }
  }
  if (Object.keys(eigenschaften).length) element.eigenschaften = eigenschaften
  return element
}
