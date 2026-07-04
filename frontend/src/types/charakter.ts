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

export type TalentZahlung = 'slot' | 'handicap_punkte' | 'aufstieg'

export interface TalentEffektSnapshot {
  handicaps?: string[]
  talente?: string[]
  maechte?: string[]
  attribut_stufen?: [string, string][]
  fertigkeit_links?: Record<string, string | null>
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
  // Ausrüstung: {name: {anzahl, angelegt}}; Geld wird in /berechne hergeleitet
  ausruestung_selected?: Record<string, { anzahl: number; angelegt?: boolean }>
  ausruestung_ausgegeben?: number
  startgeld_bonus_punkte?: number
  // Cyberware (SciFi-Kompendium)
  cyberware_installationen?: Record<string, number>
  cyberware_ausgegeben?: number
  cyberware_nebenwirkungen?: { wurf: number; name: string; effekt: string }[]
  // Superkräfte (Superkräfte-Kompendium)
  superkraft_stufe?: string
  selected_superkraefte?: Record<string, { punkte: number; modifikatoren: Record<string, number> }>
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
    // Snapshots angewendeter Spezial-Wahlen (backend/app/services/volk_wahlen.py)
    wahlen?: Record<
      string,
      {
        typ: string
        ziel?: string
        ah_talent?: string
        fertigkeit?: string
        handicap?: string
        malus?: number
        label?: string
        entfernt?: boolean
        war_untrainiert?: boolean
        delta?: number
        talent_hinzugefuegt?: boolean
      }
    >
  }
  // Zahlungsquelle je gekaufter Talent-Kopie für korrekte Rückerstattung
  // beim Entfernen (Altbestand: einzelner String statt Liste)
  talent_zahlungen?: Record<string, TalentZahlung | TalentZahlung[]>
  // Snapshot der Auto-Effekte gewählter Talente (Berserker, AH-Auto-Handicaps, ...)
  // — eine Liste je Kopie bei Mehrfachauswahl (Altbestand: einzelnes Objekt)
  talent_effekte?: Record<string, TalentEffektSnapshot | TalentEffektSnapshot[]>
}

export interface AbgeleiteteWerte {
  parade: number
  robustheit: number
  bewegungsweite: number
  groesse: number
  bennys: number
  panzerung: number
  vermoegen: number
  startkapital_gesamt: number
  traglast: number
  gesamtgewicht: number
  // nur in Cyberware-Settings (SciFi-Kompendium)
  cyberware?: { stress: number; stresslimit: number; stress_maximum: number; ueber_limit: number }
  // nur in Superkräfte-Settings
  superkraefte?: {
    stufe: string
    budget: number
    ausgegeben: number
    verbleibend: number
    kraftobergrenze: number
    talent_gewaehlt: boolean
  }
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
