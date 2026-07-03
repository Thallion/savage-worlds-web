export interface WuerfelState {
  value: number
  modifier: number
  typ: string
}

export interface FertigkeitState {
  fertigkeit_name: string
  grundfertigkeit: boolean
  ausgewaehlt: boolean
  aktiv: boolean
  wuerfel: WuerfelState
  attribut: string | null
  custom?: boolean
}

export interface AttributState {
  attribut_name: string
  wert: number
  modifier: number
}

export interface CharakterDaten {
  profil_daten: Record<string, string>
  active_setting_name: string
  char_gen_completed: boolean
  attribute: Record<string, AttributState>
  fertigkeiten: Record<string, FertigkeitState>
  selected_handicaps: string[]
  selected_talente: string[]
  selected_maechte: string[]
  voelker_selected: Record<string, any>
  verbleibende_attributsteigerungen?: number
  verbleibende_fertigkeitssteigerungen?: number
  maximale_attributsteigerungen?: number
  maximale_fertigkeitssteigerungen?: number
  gesamt_handicap_punkte?: number
  verbleibende_handicap_punkte?: number
  aufstiege_gesamt?: number
  verbleibende_aufstiege?: number
  verbleibende_talente?: number
  settingregeln?: Record<string, boolean>
  volk_effekte?: {
    attribute: Record<string, number>
    fertigkeiten: Record<string, { war_untrainiert: boolean; delta: number }>
    talente: string[]
    handicaps: string[]
    talent_slots?: number
    wahl?: { typ: 'talent' | 'fertigkeitspunkte' | 'attribut'; ziel?: string; feld?: string }
  }
  // Zahlungsquelle je gekauftem Talent für korrekte Rückerstattung beim Entfernen
  talent_zahlungen?: Record<string, 'slot' | 'handicap_punkte'>
  // Snapshot der Auto-Effekte gewählter Talente (Berserker, AH-Auto-Handicaps, ...)
  talent_effekte?: Record<
    string,
    {
      handicaps?: string[]
      talente?: string[]
      maechte?: string[]
      attribut_stufen?: [string, string][]
      fertigkeit_links?: Record<string, string | null>
    }
  >
}

export interface AbgeleiteteWerte {
  parade: number
  robustheit: number
  bewegungsweite: number
  groesse: number
  bennys: number
  machtpunkte: number
  verbleibende_maechte: number
  verbleibende_attributsteigerungen: number
  verbleibende_fertigkeitssteigerungen: number
  verbleibende_handicap_punkte: number
  verbleibende_talente: number
  verbleibende_aufstiege: number
  aufstiege_gesamt: number
  rang: string
}

export interface CharakterListItem {
  id: number
  char_name: string
  active_setting_name: string
  char_gen_completed: boolean
  aktualisiert_am: string
}

export interface CharakterDetail extends CharakterListItem {
  charakter_daten: CharakterDaten
  erstellt_am: string
}
