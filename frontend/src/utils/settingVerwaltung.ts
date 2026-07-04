// Anzeige-Namen der Setting-Kollektionen (Spiegel von
// backend/app/services/setting_verwaltung.py)

export const TYP_LABELS: Record<string, string> = {
  voelker: 'Völker',
  attribute: 'Attribute',
  fertigkeiten_daten: 'Fertigkeiten',
  talente: 'Talente',
  handicaps: 'Handicaps',
  maechte: 'Mächte',
  ausruestung: 'Ausrüstung',
  krafte: 'Superkräfte',
}

// In der Elementauswahl einzeln wählbare Typen (Attribute kommen aus der Basis)
export const WAEHLBARE_TYPEN = [
  'voelker',
  'fertigkeiten_daten',
  'talente',
  'handicaps',
  'maechte',
  'ausruestung',
  'krafte',
] as const

// Kompakte Statistik-Anzeige in Liste und Detail
export const STATISTIK_TYPEN = [
  'voelker',
  'fertigkeiten_daten',
  'talente',
  'handicaps',
  'maechte',
  'ausruestung',
] as const
