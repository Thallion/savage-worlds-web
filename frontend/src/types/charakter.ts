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

export type TalentZahlung = 'slot' | 'handicap_punkte' | 'aufstieg' | 'pathfinder_kostenlos'

export interface TalentEffektSnapshot {
  handicaps?: string[]
  talente?: string[]
  maechte?: string[]
  attribut_stufen?: [string, string][]
  fertigkeit_links?: Record<string, string | null>
}

// Steigerungs-Journal (Original: historie_view.py). entries schreibt die
// Web-App für Steigerungen nach Abschluss der Erschaffung; cost_entries ist
// das Erschaffungs-Kauf-Journal aus Kivy-Exporten/Archetypen (nur Anzeige).
export interface SteigerungsJournalEintrag {
  timestamp?: string
  type: string
  rang?: string
  details?: {
    name?: string
    von?: string | number
    nach?: string | number
    kosten?: number | string
    kosten_typ?: string
    stufe?: string
    punkte?: number
  }
}

export interface SteigerungsKostenEintrag {
  typ?: string
  name?: string
  wert?: number
  zahlungsquelle?: string
  kosten?: number | string
}

export interface SteigerungsJournal {
  entries?: SteigerungsJournalEintrag[]
  cost_entries?: SteigerungsKostenEintrag[]
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
  // Overrides aus dem Vermögens-Dialog (Original: Vermögens-Popup)
  startkapital?: number
  waehrungseinheit?: string
  // im Spiel erhaltenes (+) / verlorenes (−) Geld, fließt in die Herleitung ein
  geld_angepasst?: number
  // Cyberware (SciFi-Kompendium)
  cyberware_installationen?: Record<string, number>
  cyberware_inaktiv?: string[]
  cyberware_ausgegeben?: number
  cyberware_nebenwirkungen?: { wurf: number; name: string; effekt: string }[]
  // Effekt-Snapshots je installierter Instanz (Rücknahme bei Deinstallation)
  cyberware_effekte?: Record<
    string,
    {
      konfiguration?: Record<string, string>
      attribut?: string
      fertigkeit_schritte?: Record<string, string[]>
      chip?: { fertigkeit: string; alter_wert: number; alter_modifier: number; war_ausgewaehlt: boolean }
      talente?: string[]
    }[]
  >
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
  steigerungs_journal?: SteigerungsJournal
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
  // Savage Pathfinder: gewählte kostenlose Klassen-Talente (max. 1)
  pathfinder_kostenlose_talente_gewaehlt?: number
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
  startkapital_basis: number
  waehrung: string
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
  ordner_id: number | null
  char_name: string
  active_setting_name: string
  char_gen_completed: boolean
  aktualisiert_am: string
}

export interface CharakterDetail extends CharakterListItem {
  charakter_daten: CharakterDaten
  erstellt_am: string
}

export interface Ordner {
  id: number
  name: string
  erstellt_am: string
  anzahl_charaktere: number
}

// Schreibgeschützte Vorlage-Charaktere aus dem Original (Datei-basiert, für alle).
export interface Archetyp {
  id: string
  name: string
  setting: string
  char_gen_completed: boolean
}

export interface ArchetypOrdner {
  setting: string
  anzahl: number
}
