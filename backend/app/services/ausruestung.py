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
{name: {"anzahl": int, "angelegt": bool}}. "angelegt" gibt es nur für
Rüstungen und Schilde; angelegte Rüstung zählt mit ihrem Torso-Wert auf die
Robustheit, angelegte Schilde mit "parade" auf die Parade (siehe /berechne).
"""

STANDARD_STARTKAPITAL = 500
VERKAUF_FAKTOR_NACH_ERSCHAFFUNG = 0.5
ANLEGBARE_KATEGORIEN = ("Rüstung", "Schild")

_VERMOEGEN_TALENTE = {"Stinkreich": 5, "Reich": 3}


def startkapital_basis(setting: dict) -> float:
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

    basis = startkapital_basis(setting)
    gesamt = basis * vermoegen_multiplikator(daten) + basis * daten.get("startgeld_bonus_punkte", 0)
    # Cyberware-Installationen über dem Cyborg-Budget belasten das Geld mit
    return gesamt - daten.get("ausruestung_ausgegeben", 0) - geld_belastung(daten, setting), gesamt


def kaufe_ausruestung(daten: dict, setting: dict, item_name: str) -> tuple[bool, str]:
    item = setting.get("ausruestung", {}).get(item_name)
    if not item:
        return False, f"Ausrüstung '{item_name}' nicht gefunden"

    kosten = item.get("kosten", 0) or 0
    verfuegbar, _ = verfuegbares_geld(daten, setting)
    if kosten > verfuegbar:
        return False, f"Nicht genug Geld ({kosten:g} benötigt, {verfuegbar:g} verfügbar)"

    eintrag = daten.setdefault("ausruestung_selected", {}).setdefault(
        item_name, {"anzahl": 0, "angelegt": False}
    )
    eintrag["anzahl"] += 1
    daten["ausruestung_ausgegeben"] = daten.get("ausruestung_ausgegeben", 0) + kosten
    return True, ""


def verkaufe_ausruestung(daten: dict, setting: dict, item_name: str) -> tuple[bool, str]:
    eintrag = daten.get("ausruestung_selected", {}).get(item_name)
    if not eintrag or eintrag.get("anzahl", 0) <= 0:
        return False, f"'{item_name}' ist nicht im Besitz"

    kosten = setting.get("ausruestung", {}).get(item_name, {}).get("kosten", 0) or 0
    # Während der Erschaffung ist Verkaufen ein Zurücknehmen der Auswahl
    # (volle Erstattung); danach gilt der Original-Wiederverkaufswert von 50 %
    faktor = VERKAUF_FAKTOR_NACH_ERSCHAFFUNG if daten.get("char_gen_completed") else 1.0
    eintrag["anzahl"] -= 1
    if eintrag["anzahl"] <= 0:
        del daten["ausruestung_selected"][item_name]
    daten["ausruestung_ausgegeben"] = daten.get("ausruestung_ausgegeben", 0) - kosten * faktor
    return True, ""


def setze_angelegt(daten: dict, setting: dict, item_name: str, angelegt: bool) -> tuple[bool, str]:
    eintrag = daten.get("ausruestung_selected", {}).get(item_name)
    if not eintrag or eintrag.get("anzahl", 0) <= 0:
        return False, f"'{item_name}' ist nicht im Besitz"

    kategorie = setting.get("ausruestung", {}).get(item_name, {}).get("kategorie")
    if kategorie not in ANLEGBARE_KATEGORIEN:
        return False, f"'{item_name}' kann nicht angelegt werden (nur Rüstungen und Schilde)"

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


def panzerung_torso(daten: dict, setting: dict) -> int:
    """Angelegte Rüstung am Torso zählt nach SWAE auf die Robustheit."""
    return sum(item.get("torso", 0) or 0 for item in _angelegte_items(daten, setting, "Rüstung"))


def schild_parade(daten: dict, setting: dict) -> int:
    return sum(item.get("parade", 0) or 0 for item in _angelegte_items(daten, setting, "Schild"))


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
