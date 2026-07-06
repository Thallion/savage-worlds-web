"""Cyberware inkl. Stress (Original: cyberware_funktionen.py, SciFi-Kompendium).

Regeln wie im Original:

- Stresslimit (weich)   = min(Willenskraft, Konstitution) // 2 + Boni
- Stress-Maximum (hart) = min(Willenskraft, Konstitution) + Boni
  Boni kommen aus Talenten mit "cyberware_effekte" (stresslimit_bonus /
  stress_maximum_bonus, z. B. Kybernetische Toleranz) und installierten
  Implantaten mit effekt "bonus_stress_kapazitaet" (Ersatzorgane).
- Überschreitet der Gesamtstress das Limit, drohen Nebenwirkungen (W20 auf
  setting["cyberware_nebenwirkungen"]); über dem Maximum wird die
  Installation abgelehnt.
- Talent "Cyborg" bringt ein zweckgebundenes Implantat-Budget
  (cyberware_effekte.cyberware_budget); Installationen zehren erst dieses
  Budget auf, der Rest geht vom normalen Geld ab.
- Deinstallation: während der Erschaffung volle Erstattung (Auswahl
  zurücknehmen); danach keine Erstattung plus 25 % Deinstallationskosten
  (deinstallations_kosten_faktor aus cyberware_config.json).

Installierte Implantate lassen sich an- und abschalten (Original:
aktiviere_cyberware/deaktiviere_cyberware). Deaktivierte Implantate bleiben
installiert (Stress und Deinstallationskosten unverändert), aber ihre
Stat-Effekte greifen nicht mehr. Abgeschaltete Implantat-Namen stehen in
daten["cyberware_inaktiv"].

Installationen liegen in daten["cyberware_installationen"] = {name: anzahl},
das Kauf-Journal in daten["cyberware_ausgegeben"], erlittene Nebenwirkungen
in daten["cyberware_nebenwirkungen"] (Liste von {wurf, name, effekt}).
"""

import random

from app.services.charakter_init import load_config

KATEGORIE = "Cyberware"

# Effekte installierter Implantate, die in die abgeleiteten Werte fließen
_STAT_EFFEKTE = {
    "robustheit_bonus": "robustheit",
    "bewegungsweite_bonus": "bewegungsweite",
    "groesse_bonus": "groesse",
    "panzerung_bonus": "panzerung",
    "natuerliche_panzerung": "panzerung",
}


def _config() -> dict:
    return load_config("cyberware_config.json")


def ist_cyberware_setting(setting_name: str) -> bool:
    return setting_name in _config().get("cyberware_settings", [])


def cyberware_items(setting: dict) -> dict:
    return {
        name: item
        for name, item in setting.get("ausruestung", {}).items()
        if item.get("kategorie") == KATEGORIE
    }


def _installierte_items(daten: dict, setting: dict):
    items = cyberware_items(setting)
    for name, anzahl in daten.get("cyberware_installationen", {}).items():
        item = items.get(name)
        if item and anzahl > 0:
            yield item, anzahl


def ist_aktiv(daten: dict, item_name: str) -> bool:
    """Ein installiertes Implantat gilt als aktiv, solange es nicht auf der
    Inaktiv-Liste steht (Default: aktiv)."""
    return item_name not in daten.get("cyberware_inaktiv", [])


def _talent_cyberware_effekte(daten: dict, setting: dict) -> dict:
    summen = {"stresslimit_bonus": 0, "stress_maximum_bonus": 0, "cyberware_budget": 0}
    talente = setting.get("talente", {})
    for name in daten.get("selected_talente", []):
        effekte = talente.get(name, {}).get("cyberware_effekte") or {}
        for feld in summen:
            summen[feld] += effekte.get(feld, 0)
    return summen


def _implantat_stress_bonus(daten: dict, setting: dict) -> int:
    return sum(
        (item.get("effekte") or {}).get("bonus_stress_kapazitaet", 0) * anzahl
        for item, anzahl in _installierte_items(daten, setting)
    )


def stress_aktuell(daten: dict, setting: dict) -> int:
    return sum((item.get("stress", 0) or 0) * anzahl for item, anzahl in _installierte_items(daten, setting))


def stresslimit(daten: dict, setting: dict) -> int:
    wil = daten.get("attribute", {}).get("Willenskraft", {}).get("wert", 4)
    kon = daten.get("attribute", {}).get("Konstitution", {}).get("wert", 4)
    boni = _talent_cyberware_effekte(daten, setting)
    limit = min(wil, kon) // 2 + boni["stresslimit_bonus"] + _implantat_stress_bonus(daten, setting)
    return max(0, limit)


def stress_maximum(daten: dict, setting: dict) -> int:
    wil = daten.get("attribute", {}).get("Willenskraft", {}).get("wert", 4)
    kon = daten.get("attribute", {}).get("Konstitution", {}).get("wert", 4)
    boni = _talent_cyberware_effekte(daten, setting)
    maximum = min(wil, kon) + boni["stress_maximum_bonus"] + _implantat_stress_bonus(daten, setting)
    return max(0, maximum)


def cyberware_budget(daten: dict, setting: dict) -> float:
    """Zweckgebundenes Implantat-Budget aus Talenten (Cyborg)."""
    return _talent_cyberware_effekte(daten, setting)["cyberware_budget"]


def geld_belastung(daten: dict, setting: dict) -> float:
    """Anteil der Cyberware-Ausgaben, der das normale Geld belastet
    (alles über dem zweckgebundenen Budget)."""
    return max(0.0, daten.get("cyberware_ausgegeben", 0) - cyberware_budget(daten, setting))


def stat_boni(daten: dict, setting: dict) -> dict:
    """Stat-Effekte installierter Implantate für /berechne.

    Nur aktive Implantate steuern Boni bei; deaktivierte bleiben installiert,
    ihre Stat-Effekte greifen aber nicht."""
    boni = {"robustheit": 0, "bewegungsweite": 0, "groesse": 0, "panzerung": 0}
    items = cyberware_items(setting)
    for name, anzahl in daten.get("cyberware_installationen", {}).items():
        item = items.get(name)
        if not item or anzahl <= 0 or not ist_aktiv(daten, name):
            continue
        for effekt, wert in (item.get("effekte") or {}).items():
            stat = _STAT_EFFEKTE.get(effekt)
            if stat and isinstance(wert, (int, float)):
                boni[stat] += wert * anzahl
    return boni


def installiere(daten: dict, setting: dict, item_name: str, geld_verfuegbar: float) -> tuple[bool, str]:
    """geld_verfuegbar: aktuell verfügbares Geld (inkl. bereits abgezogener
    Cyberware-Belastung), gegen das der Budget-Überhang geprüft wird."""
    if not ist_cyberware_setting(daten.get("active_setting_name", "")):
        return False, "Dieses Setting nutzt kein Cyberware-System"

    item = cyberware_items(setting).get(item_name)
    if not item:
        return False, f"Cyberware '{item_name}' nicht gefunden"

    installationen = daten.setdefault("cyberware_installationen", {})
    maximal = item.get("max_installationen", 1)
    if maximal not in (None, -1) and installationen.get(item_name, 0) >= maximal:
        return False, f"'{item_name}' ist maximal {maximal}× installierbar"

    neuer_stress = stress_aktuell(daten, setting) + (item.get("stress", 0) or 0)
    maximum = stress_maximum(daten, setting)
    if neuer_stress > maximum:
        return False, (
            f"Stress-Maximum überschritten ({neuer_stress} > {maximum}) — "
            "Installation nicht möglich"
        )

    kosten = item.get("kosten", 0) or 0
    ausgegeben = daten.get("cyberware_ausgegeben", 0)
    budget = cyberware_budget(daten, setting)
    # Nur der Anteil über dem zweckgebundenen Budget belastet das Geld
    zusatz_belastung = max(0.0, ausgegeben + kosten - budget) - max(0.0, ausgegeben - budget)
    if zusatz_belastung > geld_verfuegbar:
        return False, f"Nicht genug Geld ({zusatz_belastung:g} benötigt, {geld_verfuegbar:g} verfügbar)"

    installationen[item_name] = installationen.get(item_name, 0) + 1
    daten["cyberware_ausgegeben"] = ausgegeben + kosten

    limit = stresslimit(daten, setting)
    if neuer_stress > limit:
        return True, (
            f"Installiert — Stresslimit überschritten ({neuer_stress} > {limit}): "
            "Nebenwirkung auswürfeln!"
        )
    return True, ""


def deinstalliere(daten: dict, setting: dict, item_name: str) -> tuple[bool, str]:
    installationen = daten.get("cyberware_installationen", {})
    if installationen.get(item_name, 0) <= 0:
        return False, f"'{item_name}' ist nicht installiert"

    kosten = cyberware_items(setting).get(item_name, {}).get("kosten", 0) or 0
    installationen[item_name] -= 1
    if installationen[item_name] <= 0:
        del installationen[item_name]
        inaktiv = daten.get("cyberware_inaktiv")
        if inaktiv and item_name in inaktiv:
            inaktiv.remove(item_name)

    if daten.get("char_gen_completed"):
        # Original: keine Erstattung, Deinstallation kostet zusätzlich 25 %
        faktor = _config().get("deinstallations_kosten_faktor", 0.25)
        daten["cyberware_ausgegeben"] = daten.get("cyberware_ausgegeben", 0) + kosten * faktor
        return True, f"Deinstalliert — Eingriff kostet {kosten * faktor:g}"

    daten["cyberware_ausgegeben"] = daten.get("cyberware_ausgegeben", 0) - kosten
    return True, ""


def setze_aktiv(daten: dict, item_name: str, aktiv: bool) -> tuple[bool, str]:
    """Schaltet ein installiertes Implantat an oder ab. Deaktivierte Implantate
    bleiben installiert, ihre Stat-Effekte greifen aber nicht mehr."""
    installationen = daten.get("cyberware_installationen", {})
    if installationen.get(item_name, 0) <= 0:
        return False, f"'{item_name}' ist nicht installiert"

    inaktiv = daten.setdefault("cyberware_inaktiv", [])
    if aktiv:
        if item_name not in inaktiv:
            return False, f"'{item_name}' ist bereits aktiv"
        inaktiv.remove(item_name)
        return True, f"'{item_name}' aktiviert"

    if item_name in inaktiv:
        return False, f"'{item_name}' ist bereits inaktiv"
    inaktiv.append(item_name)
    return True, f"'{item_name}' deaktiviert"


def wuerfle_nebenwirkung(daten: dict, setting: dict, wurf: int | None = None) -> tuple[bool, str]:
    tabelle = setting.get("cyberware_nebenwirkungen") or {}
    if not tabelle:
        return False, "Dieses Setting hat keine Nebenwirkungstabelle"

    wurf = wurf if wurf is not None else random.randint(1, 20)
    eintrag = None
    for bereich, daten_eintrag in tabelle.items():
        teile = bereich.split("-")
        von = int(teile[0])
        bis = int(teile[-1])
        if von <= wurf <= bis:
            eintrag = daten_eintrag
            break
    if not eintrag:
        return False, f"Kein Tabelleneintrag für Wurf {wurf}"

    daten.setdefault("cyberware_nebenwirkungen", []).append(
        {"wurf": wurf, "name": eintrag.get("name", ""), "effekt": eintrag.get("effekt", "")}
    )
    return True, f"Nebenwirkung ({wurf}): {eintrag.get('name')} — {eintrag.get('effekt')}"
