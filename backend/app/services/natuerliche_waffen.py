"""Natürliche Waffen (Klauen, Biss, Hörner, waffenlose Schläge).

Der Bestand wird nicht fortgeschrieben, sondern bei jeder Änderung neu aus
Abstammung + gewählten Talenten abgeleitet und mit dem Inventar abgeglichen
(synchronisiere). Das ist nötig, weil Talente vorhandene Waffen verbessern
(Kampfkünstler W4 -> Kampfkunstmeister W6 -> Schläger W8, Raufbold steigert
Klauen der Abstammung) und ein Snapshot je Talent diese Ketten nicht sauber
zurücknehmen könnte.

Quellen, in dieser Reihenfolge:

1. Abstammung, effects.spezielle_effekte: native Abstammungen setzen nur ein
   Flag ({"klauen": true}) und nennen den Schaden im Fließtext von
   "besonderheiten" ("Klauen (Stä+W4 Schaden, PB 2)"); eigene Abstammungen aus
   volkseigenarten_config.json liefern den Würfel direkt ({"klauen": "W6",
   "panzerbrechend": 2}).
2. Abstammung, "besonderheiten" ohne passendes Flag ("Natürliche Waffen
   (Biss: Stä+W4)", z. B. Horror-Vampir). Bedingte Formulierungen werden
   übersprungen: Alternativfähigkeiten (optionaler Tausch) und
   formabhängige Angaben ("Hybridform: ...", z. B. Horror-Werwolf).
3. Talente aus gamelogic/config/natuerliche_waffen_config.json, je gewählter
   Kopie in Konfigurationsreihenfolge.

Das Ergebnis sind Namen von Ausrüstungs-Einträgen der Kategorie "Waffe"
(Unterkategorie "Natürliche Waffe"), die in jedem Setting vorliegen.
"""

import re

from app.services.charakter_init import load_config

STANDARD_WUERFEL = "W4"
_CONFIG_DATEI = "natuerliche_waffen_config.json"

# besonderheiten-Zeile je Gruppe (native Abstammungen)
_ZEILEN_MUSTER = {
    "biss_klauen": r"Biss\s*(?:/|oder)\s*Klaue|Klauen?\s*/\s*(?:Biss|Zähne)",
    "klauen": r"\bKlauen\b",
    "biss": r"\bBiss\b|\bReißzähne\b",
    "hoerner": r"\bH[öo]rn",
}
# Reihenfolge: die kombinierte Gruppe zuerst, damit "Biss/Klauen" nicht als
# "Biss" durchgeht
_GRUPPEN_REIHENFOLGE = ("biss_klauen", "klauen", "biss", "hoerner", "unbewaffnet")

_WUERFEL_MUSTER = re.compile(r"St[äa](?:rke)?\s*\+\s*(W\d+)")
_PB_MUSTER = re.compile(r"\b(?:PB|AP)\s*\+?\s*(\d+)")
# Zeilen, die die Waffe nur unter Bedingungen gewähren
_BEDINGT_MUSTER = re.compile(r"Alternativfähigkeit|\b\w*form\s*:", re.IGNORECASE)
_NATUERLICHE_WAFFE_MUSTER = re.compile(r"Nat[üu]rliche\s+Waffen?", re.IGNORECASE)


def _config() -> dict:
    return load_config(_CONFIG_DATEI)


def waffen_name(gruppe_label: str, wuerfel: str, pb: int = 0) -> str:
    pb_teil = f", PB {pb}" if pb else ""
    return f"{gruppe_label} (Stä+{wuerfel}{pb_teil})"


def _steigere(wuerfel: str | None, stufen: int, kette: list[str]) -> str | None:
    """Erhöht um n Würfeltypen, begrenzt auf das Ende der Kette."""
    if wuerfel not in kette:
        return wuerfel
    return kette[min(kette.index(wuerfel) + stufen, len(kette) - 1)]


def _maximum(a: str | None, b: str | None, kette: list[str]) -> str | None:
    """Der höhere der beiden Würfel (unbekannte Würfel gewinnen nicht)."""
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b, key=lambda w: kette.index(w) if w in kette else -1)


def _volk_besonderheit(volk_data: dict, gruppe: str) -> str:
    muster = _ZEILEN_MUSTER.get(gruppe)
    if not muster:
        return ""
    for zeile in volk_data.get("besonderheiten") or []:
        text = str(zeile).strip()
        if _BEDINGT_MUSTER.search(text):
            continue
        if re.search(muster, text, re.IGNORECASE):
            return text
    return ""


def _aus_volk(volk_data: dict, zustand: dict, kette: list[str]) -> None:
    spezielle = ((volk_data.get("effects") or {}).get("spezielle_effekte")) or {}
    # aus der Eigenart "Klauen, Stufe 3" (volkseigenarten_config.json)
    pb_effekt = int(spezielle.get("panzerbrechend") or 0)
    zuordnung = _config().get("volkseigenarten") or {}

    gefunden: set[str] = set()
    for key, gruppe in zuordnung.items():
        wert = spezielle.get(key)
        if not wert:
            continue
        gefunden.add(gruppe)
        if isinstance(wert, str) and wert in kette:
            # eigene Abstammung: Würfel steht im Effekt; der PB-Effekt gehört
            # zur Eigenart "Klauen" und nicht zu Biss oder Hörnern
            wuerfel = wert
            pb = pb_effekt if gruppe in ("klauen", "biss_klauen") else 0
        else:
            text = _volk_besonderheit(volk_data, gruppe)
            treffer = _WUERFEL_MUSTER.search(text)
            pb_treffer = _PB_MUSTER.search(text)
            wuerfel = treffer.group(1) if treffer else STANDARD_WUERFEL
            pb = int(pb_treffer.group(1)) if pb_treffer else 0
        _setze(zustand, gruppe, wuerfel, pb, kette)

    # Abstammungen, die die Waffe nur im Text führen (z. B. Horror-Vampir)
    for zeile in volk_data.get("besonderheiten") or []:
        text = str(zeile).strip()
        if _BEDINGT_MUSTER.search(text) or not _NATUERLICHE_WAFFE_MUSTER.search(text):
            continue
        treffer = _WUERFEL_MUSTER.search(text)
        if not treffer:
            continue
        for gruppe in _GRUPPEN_REIHENFOLGE:
            muster = _ZEILEN_MUSTER.get(gruppe)
            if not muster or gruppe in gefunden or not re.search(muster, text, re.IGNORECASE):
                continue
            pb_treffer = _PB_MUSTER.search(text)
            _setze(zustand, gruppe, treffer.group(1), int(pb_treffer.group(1)) if pb_treffer else 0, kette)
            gefunden.add(gruppe)
            break


def _setze(zustand: dict, gruppe: str, wuerfel: str | None, pb: int, kette: list[str]) -> None:
    eintrag = zustand.setdefault(gruppe, {"wuerfel": None, "pb": 0})
    eintrag["wuerfel"] = _maximum(eintrag["wuerfel"], wuerfel, kette)
    eintrag["pb"] = max(eintrag["pb"], pb)


def _reihenfolge(eintrag: tuple[int, tuple[str, dict]]) -> tuple[int, int, int]:
    """Erst die Talente, die eine Waffe verleihen, dann die steigernden.

    Sonst hinge das Ergebnis an der Reihenfolge in der Konfiguration: Der Mönch
    (Waffenloser Schlag, Stä+W4) mit Kampfkünstler muss auf Stä+W6 kommen —
    Kampfkünstler steigert nur, wenn schon ein Würfel da ist.
    """
    index, (_, regel) = eintrag
    return (1 if regel.get("steigert") else 0, 0 if regel.get("grundwuerfel") else 1, index)


def _steigere_alle(zustand: dict, regel: dict, kette: list[str]) -> bool:
    """Steigert jede Gruppe, die schon einen Würfel hat (Raufbold, Schläger).

    Raufbold macht die Fäuste zur natürlichen Waffe (Stä+W4) — wer aber bereits
    eine hat (Klauen der Abstammung, Kampfkünstler, ...), steigert stattdessen
    deren Würfeltyp; Schläger steigert danach dasselbe noch einmal. Gibt False
    zurück, wenn nichts zu steigern war, damit die Regel auf ihren
    grundwuerfel zurückfallen kann.
    """
    eintraege = [e for e in zustand.values() if e["wuerfel"]]
    if not eintraege:
        return False
    for eintrag in eintraege:
        eintrag["wuerfel"] = _steigere(eintrag["wuerfel"], regel.get("steigert") or 0, kette)
    return True


def _aus_talenten(daten: dict, zustand: dict, kette: list[str]) -> None:
    gewaehlt = daten.get("selected_talente") or []
    talente = _config().get("talente") or {}
    for _, (talent_name, regel) in sorted(enumerate(talente.items()), key=_reihenfolge):
        anzahl = sum(1 for t in gewaehlt if t == talent_name)
        if not anzahl:
            continue
        gruppe = regel.get("gruppe")
        wiederholung = regel.get("wiederholung") or {}
        for kopie in range(anzahl):
            aktiv = {**regel, **wiederholung} if kopie else regel
            if aktiv.get("steigert_alle") and _steigere_alle(zustand, aktiv, kette):
                continue
            eintrag = zustand.setdefault(gruppe, {"wuerfel": None, "pb": 0})
            if aktiv.get("setzt"):
                eintrag["wuerfel"] = _maximum(eintrag["wuerfel"], aktiv["setzt"], kette)
            elif eintrag["wuerfel"] is None and aktiv.get("grundwuerfel"):
                eintrag["wuerfel"] = aktiv["grundwuerfel"]
            elif aktiv.get("steigert") and eintrag["wuerfel"]:
                eintrag["wuerfel"] = _steigere(eintrag["wuerfel"], aktiv["steigert"], kette)
            eintrag["pb"] = max(eintrag["pb"], int(aktiv.get("pb") or 0))


def abgeleitete_waffen(daten: dict) -> list[str]:
    """Namen aller Ausrüstungs-Einträge, die Abstammung und Talente stellen."""
    config = _config()
    kette = list(config.get("wuerfel_kette") or [])
    gruppen = config.get("gruppen") or {}
    zustand: dict[str, dict] = {}

    for volk_data in (daten.get("voelker_selected") or {}).values():
        if isinstance(volk_data, dict):
            _aus_volk(volk_data, zustand, kette)
    _aus_talenten(daten, zustand, kette)

    namen = []
    for gruppe in _GRUPPEN_REIHENFOLGE:
        eintrag = zustand.get(gruppe)
        if not eintrag or not eintrag["wuerfel"]:
            continue
        name = waffen_name(gruppen.get(gruppe, gruppe), eintrag["wuerfel"], eintrag["pb"])
        if name not in namen:
            namen.append(name)
    return namen


def synchronisiere(daten: dict, setting: dict | None = None) -> None:
    """Gleicht das Inventar mit den abgeleiteten natürlichen Waffen ab.

    Kostenlos und gewichtslos: die Waffen werden weder bezahlt noch erstattet.
    daten["natuerliche_waffen"] hält fest, was zuletzt automatisch gestellt
    wurde — nur diese Einträge werden wieder entfernt, selbst gekaufte bleiben.
    """
    katalog = (setting.get("ausruestung") or {}) if setting else None
    neu = abgeleitete_waffen(daten)
    if katalog is not None:
        neu = [name for name in neu if name in katalog]
    alt = daten.get("natuerliche_waffen") or []
    ausruestung = daten.setdefault("ausruestung_selected", {})

    for name in alt:
        if name in neu:
            continue
        eintrag = ausruestung.get(name)
        if not eintrag:
            continue
        eintrag["anzahl"] = eintrag.get("anzahl", 0) - 1
        if eintrag["anzahl"] <= 0:
            del ausruestung[name]

    gestellt = []
    for name in neu:
        if name not in alt and name in ausruestung:
            # bereits selbst gekauft — dann bleibt es in der Hand des Spielers
            continue
        ausruestung.setdefault(name, {"anzahl": 1, "angelegt": False})
        gestellt.append(name)

    if gestellt:
        daten["natuerliche_waffen"] = gestellt
    else:
        daten.pop("natuerliche_waffen", None)
