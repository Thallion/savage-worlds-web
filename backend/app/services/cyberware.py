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

Direkte Effekte (Original: appliziere_cyberware_effekte) verändern den
Charakter beim Installieren — Attributerhöhung, Fertigkeits-Boni,
Fertigkeitschip, gewährte Talente. Wie bei talent_effekte wird pro Instanz
ein Snapshot in daten["cyberware_effekte"][name] abgelegt (Liste), damit die
Deinstallation genau diese Effekte zurücknimmt. Konfigurierbare Implantate
(z. B. welches Attribut) brauchen eine konfiguration-Wahl; deaktivierte
Implantate behalten wie im Original ihre direkten Effekte, nur die
abgeleiteten Stat-Boni ruhen.
"""

import random

from app.services.charakter_init import load_config

KATEGORIE = "Cyberware"
MAX_WUERFEL = 12
MIN_WUERFEL = 4

# Effekte installierter Implantate, die in die abgeleiteten Werte fließen
_STAT_EFFEKTE = {
    "robustheit_bonus": "robustheit",
    "bewegungsweite_bonus": "bewegungsweite",
    "groesse_bonus": "groesse",
    "panzerung_bonus": "panzerung",
    "natuerliche_panzerung": "panzerung",
}

# Traglast: +1 virtueller Stärke-Würfeltyp = +2 Stärke-Punkte × 10 kg
_TRAGLAST_KG_PRO_STUFE = 20


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
    boni = {"robustheit": 0, "bewegungsweite": 0, "groesse": 0, "panzerung": 0, "traglast_kg": 0}
    items = cyberware_items(setting)
    for name, anzahl in daten.get("cyberware_installationen", {}).items():
        item = items.get(name)
        if not item or anzahl <= 0 or not ist_aktiv(daten, name):
            continue
        effekte = item.get("effekte") or {}
        for effekt, wert in effekte.items():
            stat = _STAT_EFFEKTE.get(effekt)
            if stat and isinstance(wert, (int, float)):
                boni[stat] += wert * anzahl
        boni["traglast_kg"] += (
            effekte.get("traglast_staerke_bonus", 0) * _TRAGLAST_KG_PRO_STUFE * anzahl
        )
    return boni


# ---- Direkte Effekte (Original: appliziere_cyberware_effekte) ----


def benoetigte_konfiguration(item: dict) -> dict | None:
    """Wahl, die ein Implantat vor der Installation braucht (Original:
    get_cyberware_konfiguration). typ ist "attribut", "fertigkeit" oder
    "talent"; die Optionen ergeben sich aus dem Charakter bzw. Setting."""
    effekte = item.get("effekte") or {}
    if effekte.get("attribut_erhoehung"):
        return {"typ": "attribut", "label": "Attribut wählen (+1 Würfeltyp)"}
    fb = effekte.get("fertigkeit_bonus")
    if isinstance(fb, dict) and fb.get("fertigkeit") == "waehlbar":
        return {"typ": "fertigkeit", "label": f"Fertigkeit wählen (+{fb.get('bonus', 1)})"}
    if effekte.get("fertigkeitschip"):
        ziel = effekte.get("fertigkeit_wert", 6)
        return {"typ": "fertigkeit", "label": f"Fertigkeit wählen (wird auf W{ziel} gesetzt)"}
    if effekte.get("kampftalent_gewaehrt"):
        return {"typ": "talent", "label": "Kampftalent wählen"}
    return None


def _fertigkeit_erhoehen(fert: dict) -> str:
    """Ein Steigerungs-Schritt wie im Original (W4−2 → W4 → W6 … → W12 → +1).
    Gibt den Marker für die Rücknahme zurück."""
    w = fert.setdefault("wuerfel", {"value": MIN_WUERFEL, "modifier": -2, "typ": "fertigkeit"})
    if w.get("modifier", 0) == -2:
        w["modifier"] = 0
        fert["ausgewaehlt"] = True
        return "einstieg"
    if w.get("value", MIN_WUERFEL) < MAX_WUERFEL:
        w["value"] = w.get("value", MIN_WUERFEL) + 2
        return "wert"
    w["modifier"] = w.get("modifier", 0) + 1
    return "modifier"


def _fertigkeit_schritt_zurueck(fert: dict, marker: str) -> None:
    w = fert.setdefault("wuerfel", {"value": MIN_WUERFEL, "modifier": 0, "typ": "fertigkeit"})
    if marker == "einstieg":
        w["modifier"] = -2
        fert["ausgewaehlt"] = fert.get("grundfertigkeit", False)
    elif marker == "wert":
        w["value"] = max(MIN_WUERFEL, w.get("value", MIN_WUERFEL) - 2)
    else:
        w["modifier"] = w.get("modifier", 0) - 1


def _fertigkeits_boni(effekte: dict, konfig: dict) -> list[tuple[str, int]]:
    """(Fertigkeit, Bonus)-Paare eines Implantats: fertigkeit_bonus
    (wählbar oder feste Liste) plus athletik_bonus/wahrnehmung_bonus."""
    boni: list[tuple[str, int]] = []
    fb = effekte.get("fertigkeit_bonus")
    if isinstance(fb, dict):
        if fb.get("fertigkeit") == "waehlbar" and konfig.get("fertigkeit"):
            boni.append((konfig["fertigkeit"], fb.get("bonus", 1)))
        for fert_name in fb.get("fertigkeiten") or []:
            boni.append((fert_name, fb.get("bonus", 1)))
    for feld, fert_name in (("athletik_bonus", "Athletik"), ("wahrnehmung_bonus", "Wahrnehmung")):
        if effekte.get(feld):
            boni.append((fert_name, effekte[feld]))
    return boni


def _implantat_talente(effekte: dict, konfig: dict) -> list[str]:
    talente = []
    if effekte.get("talent_gewaehrt"):
        talente.append(effekte["talent_gewaehrt"])
    if effekte.get("kampftalent_gewaehrt") and konfig.get("talent"):
        talente.append(konfig["talent"])
    return talente


def _wende_effekte_an(daten: dict, item: dict, konfiguration: dict | None) -> dict:
    """Wendet die direkten Effekte einer Installation an und gibt den
    Snapshot für die spätere Rücknahme zurück."""
    effekte = item.get("effekte") or {}
    konfig = konfiguration or {}
    snapshot: dict = {}
    if konfig:
        snapshot["konfiguration"] = konfig

    # Attributerhöhung: +1 Würfeltyp, Obergrenze W12 (Original: min(wert+2, 12))
    if effekte.get("attribut_erhoehung"):
        attr = daten.get("attribute", {}).get(konfig.get("attribut", ""))
        if attr and attr.get("wert", MIN_WUERFEL) < MAX_WUERFEL:
            attr["wert"] = attr.get("wert", MIN_WUERFEL) + 2
            snapshot["attribut"] = konfig["attribut"]

    schritte: dict = {}
    for fert_name, bonus in _fertigkeits_boni(effekte, konfig):
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if not fert:
            continue
        marker = schritte.setdefault(fert_name, [])
        for _ in range(bonus):
            marker.append(_fertigkeit_erhoehen(fert))
    if schritte:
        snapshot["fertigkeit_schritte"] = schritte

    if effekte.get("fertigkeitschip") and konfig.get("fertigkeit"):
        fert = daten.get("fertigkeiten", {}).get(konfig["fertigkeit"])
        if fert:
            w = fert.setdefault("wuerfel", {"value": MIN_WUERFEL, "modifier": -2, "typ": "fertigkeit"})
            snapshot["chip"] = {
                "fertigkeit": konfig["fertigkeit"],
                "alter_wert": w.get("value", MIN_WUERFEL),
                "alter_modifier": w.get("modifier", -2),
                "war_ausgewaehlt": fert.get("ausgewaehlt", False),
            }
            w["modifier"] = 0
            w["value"] = max(w.get("value", MIN_WUERFEL), effekte.get("fertigkeit_wert", 6))
            fert["ausgewaehlt"] = True

    neu = [
        t for t in _implantat_talente(effekte, konfig)
        if t not in daten.setdefault("selected_talente", [])
    ]
    if neu:
        daten["selected_talente"].extend(neu)
        snapshot["talente"] = neu

    return snapshot


def _entferne_effekte(daten: dict, item_name: str) -> None:
    """Nimmt die Effekte der zuletzt installierten Instanz zurück."""
    effekte_map = daten.get("cyberware_effekte") or {}
    snapshots = effekte_map.get(item_name) or []
    if not snapshots:
        return
    snap = snapshots.pop()
    if not snapshots:
        effekte_map.pop(item_name, None)
    if not effekte_map:
        daten.pop("cyberware_effekte", None)

    attr_name = snap.get("attribut")
    if attr_name:
        attr = daten.get("attribute", {}).get(attr_name)
        if attr:
            attr["wert"] = max(MIN_WUERFEL, attr.get("wert", MIN_WUERFEL) - 2)

    for fert_name, marker in (snap.get("fertigkeit_schritte") or {}).items():
        fert = daten.get("fertigkeiten", {}).get(fert_name)
        if fert:
            for m in reversed(marker):
                _fertigkeit_schritt_zurueck(fert, m)

    chip = snap.get("chip")
    if chip:
        fert = daten.get("fertigkeiten", {}).get(chip.get("fertigkeit", ""))
        if fert:
            w = fert.setdefault("wuerfel", {"typ": "fertigkeit"})
            w["value"] = chip.get("alter_wert", MIN_WUERFEL)
            w["modifier"] = chip.get("alter_modifier", -2)
            fert["ausgewaehlt"] = chip.get("war_ausgewaehlt", False)

    for t in snap.get("talente") or []:
        if t in daten.get("selected_talente", []):
            daten["selected_talente"].remove(t)


def rekonstruiere_effekt_snapshots(daten: dict, kivy_installationen: list[dict]) -> dict:
    """Baut die Effekt-Snapshots für importierte Kivy-Installationen nach.

    Die Effekte selbst stecken bereits in den exportierten Werten — hier wird
    nur rekonstruiert, was eine Deinstallation zurücknehmen muss. Die
    Instanzen werden rückwärts durchlaufen und die Steigerungs-Schritte auf
    einem Simulationsstand abgesenkt, damit mehrere Instanzen desselben
    Implantats zusammen exakt den Ausgangszustand ergeben."""
    sim_fertigkeiten: dict = {}
    sim_attribute: dict = {}
    ergebnis: dict = {}

    for inst in reversed(kivy_installationen):
        name = inst.get("name") or ""
        effekte = inst.get("effekte") or {}
        konfig = inst.get("konfiguration") or {}
        snapshot: dict = {}
        wahl = {k: v for k, v in konfig.items() if k in ("attribut", "fertigkeit", "talent")}
        if wahl:
            snapshot["konfiguration"] = wahl

        if effekte.get("attribut_erhoehung") and konfig.get("attribut"):
            attr = daten.get("attribute", {}).get(konfig["attribut"])
            if attr:
                stand = sim_attribute.setdefault(konfig["attribut"], attr.get("wert", MIN_WUERFEL))
                if stand > MIN_WUERFEL:
                    sim_attribute[konfig["attribut"]] = stand - 2
                    snapshot["attribut"] = konfig["attribut"]

        schritte: dict = {}
        for fert_name, bonus in _fertigkeits_boni(effekte, konfig):
            fert = daten.get("fertigkeiten", {}).get(fert_name)
            if not fert:
                continue
            w = sim_fertigkeiten.setdefault(fert_name, dict(fert.get("wuerfel") or {}))
            marker = []
            for _ in range(bonus):
                if w.get("modifier", 0) > 0:
                    w["modifier"] -= 1
                    marker.append("modifier")
                elif w.get("value", MIN_WUERFEL) > MIN_WUERFEL:
                    w["value"] = w.get("value", MIN_WUERFEL) - 2
                    marker.append("wert")
                elif w.get("modifier", 0) == 0:
                    w["modifier"] = -2
                    marker.append("einstieg")
                else:
                    break
            marker.reverse()
            if marker:
                schritte[fert_name] = marker + schritte.get(fert_name, [])
        if schritte:
            snapshot["fertigkeit_schritte"] = schritte

        # Kivy legt den Zustand vor dem Chip in der Konfiguration ab
        if effekte.get("fertigkeitschip") and konfig.get("fertigkeit"):
            if konfig["fertigkeit"] in daten.get("fertigkeiten", {}):
                snapshot["chip"] = {
                    "fertigkeit": konfig["fertigkeit"],
                    "alter_wert": konfig.get("alter_fertigkeit_wert", MIN_WUERFEL),
                    "alter_modifier": konfig.get("alter_fertigkeit_modifier", -2),
                    "war_ausgewaehlt": False,
                }

        talente = [
            t for t in _implantat_talente(effekte, konfig)
            if t in daten.get("selected_talente", [])
        ]
        if talente:
            snapshot["talente"] = talente

        if snapshot:
            ergebnis.setdefault(name, []).insert(0, snapshot)

    return ergebnis


def _kosten(item: dict, preis: float | None) -> float:
    """Abweichender Preis, sonst Katalogpreis des Implantats (Original: anpassbar)."""
    if preis is not None:
        return preis
    return item.get("kosten", 0) or 0


def installiere(
    daten: dict,
    setting: dict,
    item_name: str,
    geld_verfuegbar: float,
    preis: float | None = None,
    konfiguration: dict | None = None,
) -> tuple[bool, str]:
    """geld_verfuegbar: aktuell verfügbares Geld (inkl. bereits abgezogener
    Cyberware-Belastung), gegen das der Budget-Überhang geprüft wird.
    preis=None -> Katalogpreis; abweichend wie bei normaler Ausrüstung.
    konfiguration: Wahl für konfigurierbare Implantate, z. B. {"attribut": "Stärke"}."""
    if not ist_cyberware_setting(daten.get("active_setting_name", "")):
        return False, "Dieses Setting nutzt kein Cyberware-System"

    item = cyberware_items(setting).get(item_name)
    if not item:
        return False, f"Cyberware '{item_name}' nicht gefunden"

    konfig = konfiguration or {}
    wahl = benoetigte_konfiguration(item)
    if wahl:
        ziel = konfig.get(wahl["typ"])
        if not ziel:
            return False, f"Wahl erforderlich: {wahl['label']}"
        if wahl["typ"] == "attribut" and ziel not in daten.get("attribute", {}):
            return False, f"Attribut '{ziel}' nicht gefunden"
        if wahl["typ"] == "fertigkeit" and ziel not in daten.get("fertigkeiten", {}):
            return False, f"Fertigkeit '{ziel}' nicht gefunden"
        if wahl["typ"] == "talent" and ziel not in setting.get("talente", {}):
            return False, f"Talent '{ziel}' nicht gefunden"

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

    kosten = _kosten(item, preis)
    if kosten < 0:
        return False, "Preis darf nicht negativ sein"
    ausgegeben = daten.get("cyberware_ausgegeben", 0)
    budget = cyberware_budget(daten, setting)
    # Nur der Anteil über dem zweckgebundenen Budget belastet das Geld
    zusatz_belastung = max(0.0, ausgegeben + kosten - budget) - max(0.0, ausgegeben - budget)
    if zusatz_belastung > geld_verfuegbar:
        return False, f"Nicht genug Geld ({zusatz_belastung:g} benötigt, {geld_verfuegbar:g} verfügbar)"

    installationen[item_name] = installationen.get(item_name, 0) + 1
    daten["cyberware_ausgegeben"] = ausgegeben + kosten

    # Direkte Effekte anwenden und den Snapshot je Instanz ablegen
    snapshot = _wende_effekte_an(daten, item, konfig)
    vorhanden = (daten.get("cyberware_effekte") or {}).get(item_name) or []
    if snapshot or vorhanden:
        daten.setdefault("cyberware_effekte", {})[item_name] = vorhanden + [snapshot]

    limit = stresslimit(daten, setting)
    if neuer_stress > limit:
        return True, (
            f"Installiert — Stresslimit überschritten ({neuer_stress} > {limit}): "
            "Nebenwirkung auswürfeln!"
        )
    return True, ""


def deinstalliere(
    daten: dict, setting: dict, item_name: str, preis: float | None = None
) -> tuple[bool, str]:
    installationen = daten.get("cyberware_installationen", {})
    if installationen.get(item_name, 0) <= 0:
        return False, f"'{item_name}' ist nicht installiert"

    kosten = _kosten(cyberware_items(setting).get(item_name, {}), preis)
    if kosten < 0:
        return False, "Preis darf nicht negativ sein"
    installationen[item_name] -= 1
    _entferne_effekte(daten, item_name)
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
