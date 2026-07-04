// Sortier-Helfer für die Element-Listen (Original: RANG_MAPPING + _sort_items
// in den Kivy-Views).

export const RANG_ORDNUNG: Record<string, number> = { A: 1, F: 2, V: 3, H: 4, L: 5, WC: 6 }

/** Sortiert die Einträge eines Katalogs und liefert ein neues Objekt in
 *  Anzeige-Reihenfolge (JS behält die Einfüge-Reihenfolge von String-Keys). */
export function sortiertesObjekt(
  eintraege: Record<string, any>,
  schluessel: (name: string, wert: any) => string | number,
  absteigend: boolean,
): Record<string, any> {
  const richtung = absteigend ? -1 : 1
  const sortiert = Object.entries(eintraege).sort((a, b) => {
    const ka = schluessel(a[0], a[1])
    const kb = schluessel(b[0], b[1])
    return (ka < kb ? -1 : ka > kb ? 1 : 0) * richtung
  })
  return Object.fromEntries(sortiert)
}
