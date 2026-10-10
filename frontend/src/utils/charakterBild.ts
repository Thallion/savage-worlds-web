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
