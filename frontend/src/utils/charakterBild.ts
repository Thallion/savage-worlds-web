// Porträts: Varianten wie in backend/app/services/charakterbild.py. Die URL
// braucht keinen Login — die nicht erratbare bild_id ist die Berechtigung.
export type BildVariante = 'gross' | 'karte' | 'avatar'

export const BILD_MAX_MB = 8
export const BILD_MIN_BREITE = 200
export const BILD_MIN_HOEHE = 266
export const STANDARD_FOKUS_Y = 0.2

export function bildUrl(bildId: string | null | undefined, variante: BildVariante): string | null {
  return bildId ? `/api/bilder/${bildId}/${variante}.webp` : null
}

/** Initialen für den Platzhalter („Thorgrim Eisenbart" → „TE"). */
export function initialen(name: string | null | undefined): string {
  const teile = (name || '').trim().split(/\s+/).filter(Boolean)
  if (!teile.length) return '?'
  const erste = teile[0][0]
  const letzte = teile.length > 1 ? teile[teile.length - 1][0] : ''
  return (erste + letzte).toUpperCase()
}

// Gedeckte Töne, die zum Pergament-Look passen und in Hell/Dunkel lesbar bleiben
const PLATZHALTER_FARBEN = [
  '#8d6e63', '#6d4c41', '#5d6d3e', '#3e6d6a', '#4a5f8a',
  '#6a4c8a', '#8a4c6a', '#8a5a2b', '#55606e', '#7a6a3a',
]

/** Gleiche Farbe für alle Charaktere eines Settings. */
export function platzhalterFarbe(setting: string | null | undefined): string {
  let h = 0
  for (const zeichen of setting || '') h = (h * 31 + zeichen.charCodeAt(0)) >>> 0
  return PLATZHALTER_FARBEN[h % PLATZHALTER_FARBEN.length]
}
