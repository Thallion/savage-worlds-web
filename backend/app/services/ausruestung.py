"""Ausrüstung & Startgeld (Original: ausruestung_funktionen.py).

Geld wird nicht als Kontostand gespeichert, sondern hergeleitet:

    verfügbar = startkapital × Multiplikator
              + startkapital × eingelöste Handicap-Punkte ("startgeld")
              − ausgegeben

- startkapital kommt aus setting["startgeld"] (SWADE-Standard 500, wenn das
  Setting nichts definiert).
- Multiplikator: Handicap "Arm" halbiert (0.5), Talente "Reich" ×3 /
  "Stinkreich" ×5 (nicht kumulativ, Stinkreich zählt); Arm+Reich ist bereits
  über die Kompatibilitätsprüfung ausgeschlossen.
- "ausgegeben" ist das Kauf-Journal: Kaufen addiert die Kosten, Verkaufen
  erstattet während der Erschaffung den vollen Preis (Auswahl zurücknehmen),
  nach Abschluss wie im Original 50 %.

Gekaufte Gegenstände liegen in daten["ausruestung_selected"]:
{name: {"anzahl": int, "angelegt": bool}}. "angelegt" gibt es für Rüstungen,
Schilde und Waffen; angelegte Rüstung zählt mit ihrem Torso-Wert auf die
Robustheit, angelegte Schilde mit "parade" und angelegte (geführte) Waffen mit
ihrem Paradebonus aus der Beschreibung auf die Parade (siehe /berechne).
"""

import re

STANDARD_STARTKAPITAL = 500
VERKAUF_FAKTOR_NACH_ERSCHAFFUNG = 0.5
ANLEGBARE_KATEGORIEN = ("Rüstung", "Schild", "Waffe")

_VERMOEGEN_TALENTE = {"Stinkreich": 5, "Reich": 3}


def startkapital_basis(setting: dict, daten: dict | None = None) -> float:
    """Setting-Startgeld, überschreibbar pro Charakter (daten["startkapital"],
    Original: Vermögens-Popup der Charakterverwaltung)."""
    if daten is not None and isinstance(daten.get("startkapital"), (int, float)):
        return daten["startkapital"]
    return setting.get("startgeld") or STANDARD_STARTKAPITAL


def vermoegen_multiplikator(daten: dict) -> float:
    handicaps = daten.get("selected_handicaps", [])
    if "Arm" in handicaps or "Arm_leicht" in handicaps:
        return 0.5
    talente = daten.get("selected_talente", [])
    for name, faktor in _VERMOEGEN_TALENTE.items():
        if name in talente:
            return faktor
    return 1.0


def verfuegbares_geld(daten: dict, setting: dict) -> tuple[float, float]:
    """(aktuell verfügbar, Gesamtbudget ohne Ausgaben)."""
    from app.services.cyberware import geld_belastung

    basis = startkapital_basis(setting, daten)
    gesamt = (
        basis * vermoegen_multiplikator(daten)
        + basis * daten.get("startgeld_bonus_punkte", 0)
        # im Spiel erhaltenes/verlorenes Geld (Original: vermoegen direkt editierbar)
        + daten.get("geld_angepasst", 0)
    )
    # Cyberware-Installationen über dem Cyborg-Budget belasten das Geld mit
    return gesamt - daten.get("ausruestung_ausgegeben", 0) - geld_belastung(daten, setting), gesamt


def _stueckpreis(setting: dict, item_name: str, preis: float | None) -> float:
    """Abweichender Preis, sonst Katalogpreis des Settings (Original: anpassbar)."""
    if preis is not None:
        return preis
    return setting.get("ausruestung", {}).get(item_name, {}).get("kosten", 0) or 0


def kaufe_ausruestung(
    daten: dict, setting: dict, item_name: str, menge: int = 1, preis: float | None = None
) -> tuple[bool, str]:
    item = setting.get("ausruestung", {}).get(item_name)
    if not item:
        return False, f"Ausrüstung '{item_name}' nicht gefunden"
    if menge < 1:
        return False, "Menge muss mindestens 1 sein"

    stueckpreis = _stueckpreis(setting, item_name, preis)
    if stueckpreis < 0:
        return False, "Preis darf nicht negativ sein"

    gesamt = stueckpreis * menge
    verfuegbar, _ = verfuegbares_geld(daten, setting)
    if gesamt > verfuegbar:
        return False, f"Nicht genug Geld ({gesamt:g} benötigt, {verfuegbar:g} verfügbar)"

    eintrag = daten.setdefault("ausruestung_selected", {}).setdefault(
        item_name, {"anzahl": 0, "angelegt": False}
    )
    eintrag["anzahl"] += menge
    daten["ausruestung_ausgegeben"] = daten.get("ausruestung_ausgegeben", 0) + gesamt
    return True, ""


def verkaufe_ausruestung(
    daten: dict, setting: dict, item_name: str, menge: int = 1, preis: float | None = None
) -> tuple[bool, str]:
    eintrag = daten.get("ausruestung_selected", {}).get(item_name)
    if not eintrag or eintrag.get("anzahl", 0) <= 0:
        return False, f"'{item_name}' ist nicht im Besitz"
    if menge < 1:
        return False, "Menge muss mindestens 1 sein"

    menge = min(menge, eintrag["anzahl"])
    stueckpreis = _stueckpreis(setting, item_name, preis)
    # Während der Erschaffung ist Verkaufen ein Zurücknehmen der Auswahl
    # (volle Erstattung); danach gilt der Original-Wiederverkaufswert von 50 %
    faktor = VERKAUF_FAKTOR_NACH_ERSCHAFFUNG if daten.get("char_gen_completed") else 1.0
    eintrag["anzahl"] -= menge
    if eintrag["anzahl"] <= 0:
        del daten["ausruestung_selected"][item_name]
    daten["ausruestung_ausgegeben"] = (
        daten.get("ausruestung_ausgegeben", 0) - stueckpreis * faktor * menge
    )
    return True, ""


def setze_angelegt(daten: dict, setting: dict, item_name: str, angelegt: bool) -> tuple[bool, str]:
    eintrag = daten.get("ausruestung_selected", {}).get(item_name)
    if not eintrag or eintrag.get("anzahl", 0) <= 0:
        return False, f"'{item_name}' ist nicht im Besitz"

    kategorie = setting.get("ausruestung", {}).get(item_name, {}).get("kategorie")
    if kategorie not in ANLEGBARE_KATEGORIEN:
        return False, f"'{item_name}' kann nicht angelegt werden (nur Rüstungen, Schilde und Waffen)"

    eintrag["angelegt"] = angelegt
    return True, ""


def _angelegte_items(daten: dict, setting: dict, kategorie: str):
    ausruestung = setting.get("ausruestung", {})
    for name, eintrag in daten.get("ausruestung_selected", {}).items():
        if eintrag.get("anzahl", 0) <= 0 or not eintrag.get("angelegt"):
            continue
        item = ausruestung.get(name)
        if item and item.get("kategorie") == kategorie:
            yield item


def traegt_ruestung(daten: dict, setting: dict) -> bool:
    """Für die Effekt-Bedingung "keine_getragene_ruestung" (z. B. Kämpferische Disziplin)."""
    return next(_angelegte_items(daten, setting, "Rüstung"), None) is not None


TREFFERZONEN = ("torso", "arme", "beine", "kopf")


def _geschichtete_panzerung(werte: list[int]) -> int:
    """Mehrere Rüstungen übereinander (SWAE S. 66): die stärkste zählt voll,
    jede schwächere addiert ihren halben Wert (abgerundet)."""
    werte = sorted((w for w in werte if w > 0), reverse=True)
    if not werte:
        return 0
    return werte[0] + sum(w // 2 for w in werte[1:])


def panzerung_torso(daten: dict, setting: dict) -> int:
    """Angelegte Rüstung am Torso zählt nach SWAE auf die Robustheit."""
    return _geschichtete_panzerung(
        [item.get("torso", 0) or 0 for item in _angelegte_items(daten, setting, "Rüstung")]
    )


def _wuerfel_seiten(wert) -> int:
    m = re.search(r"\d+", str(wert or ""))
    return int(m.group()) if m else 0


def ruestung_mindeststaerke(daten: dict, setting: dict) -> int:
    """Benötigte Stärke (Würfelseiten) für die angelegten Rüstungen.

    Liegt eine schwächere Rüstung in einer Trefferzone unter einer schwereren,
    steigt die Mindeststärke der schwereren um einen Würfeltyp (max. W12).
    """
    ruestungen = list(_angelegte_items(daten, setting, "Rüstung"))
    benoetigt = 0
    for i, item in enumerate(ruestungen):
        seiten = _wuerfel_seiten(item.get("mindeststaerke"))
        ueberlagert = any(
            (item.get(zone) or 0) > 0
            and 0 < (andere.get(zone) or 0)
            # Gleichstand: nur eine der beiden gilt als die schwerere
            and ((andere.get(zone) or 0) < item[zone] or ((andere.get(zone) or 0) == item[zone] and j > i))
            for j, andere in enumerate(ruestungen)
            if j != i
            for zone in TREFFERZONEN
        )
        if ueberlagert and seiten:
            seiten = min(seiten + 2, 12)
        benoetigt = max(benoetigt, seiten)
    return benoetigt


def schild_mindeststaerke(daten: dict, setting: dict) -> int:
    """Benötigte Stärke (Würfelseiten) für die angelegten Schilde."""
    return max(
        (_wuerfel_seiten(item.get("mindeststaerke")) for item in _angelegte_items(daten, setting, "Schild")),
        default=0,
    )


def _fehlende_wuerfeltypen(staerke: int, mindeststaerke: int) -> int:
    return max(0, mindeststaerke - staerke) // 2


def ruestung_malus(daten: dict, setting: dict) -> int:
    """Zu schwere Rüstung bzw. zu schwerer Schild (SWAE): −1 je Würfeltyp, den
    die Stärke unter der Mindeststärke liegt, auf Geschicklichkeit und deren
    Fertigkeiten. Rüstung und Schild zählen getrennt und addieren sich."""
    staerke = daten.get("attribute", {}).get("Stärke", {}).get("wert", 4)
    return -(
        _fehlende_wuerfeltypen(staerke, ruestung_mindeststaerke(daten, setting))
        + _fehlende_wuerfeltypen(staerke, schild_mindeststaerke(daten, setting))
    )


def ruestung_malus_ziele(daten: dict, setting: dict) -> list[str]:
    """Geschicklichkeit und alle Fertigkeiten des Charakters, die darauf basieren."""
    fertigkeit_attribute = setting.get("fertigkeiten_daten", {})
    return ["Geschicklichkeit"] + [
        name
        for name in daten.get("fertigkeiten", {})
        if "Geschicklichkeit" in (fertigkeit_attribute.get(name) or [])
    ]


def malus_fuer(werte: dict, name: str) -> int:
    """Rüstungsabzug aus /berechne für ein Attribut oder eine Fertigkeit."""
    return werte.get("ruestung_malus", 0) if name in werte.get("ruestung_malus_ziele", ()) else 0


# "Parade +1" / "Parade -1" im Beschreibungstext einer Waffe. Bedingte
# Angaben ("Parade +1 wenn zweihändig", "... beim Verteidigen") zählen nicht.
_WAFFEN_PARADE = re.compile(r"Parade\s*([+\-–−])\s*(\d+)([^,.;]*)")


def waffen_parade(item: dict) -> int:
    """Paradebonus/-malus einer Waffe, solange sie geführt wird (SWADE)."""
    for vorzeichen, wert, rest in _WAFFEN_PARADE.findall(item.get("beschreibung") or ""):
        if rest.strip():
            continue
        return -int(wert) if vorzeichen != "+" else int(wert)
    return 0


def schild_parade(daten: dict, setting: dict) -> int:
    return sum(item.get("parade", 0) or 0 for item in _angelegte_items(daten, setting, "Schild"))


def angelegte_waffen_parade(daten: dict, setting: dict) -> int:
    """Paradebonus der angelegten (geführten) Waffen, z. B. Kampfstab +1."""
    return sum(waffen_parade(item) for item in _angelegte_items(daten, setting, "Waffe"))


def gesamtgewicht(daten: dict, setting: dict) -> float:
    ausruestung = setting.get("ausruestung", {})
    return sum(
        (ausruestung.get(name, {}).get("gewicht", 0) or 0) * eintrag.get("anzahl", 0)
        for name, eintrag in daten.get("ausruestung_selected", {}).items()
    )


def traglast_kg(daten: dict, traglast_bonus: float = 0) -> float:
    """Traglast = Stärke-Würfel × 10 kg, plus Talent-Boni (traglast_kg, z. B. Kräftig)."""
    staerke = daten.get("attribute", {}).get("Stärke", {}).get("wert", 4)
    return staerke * 10 + traglast_bonus
