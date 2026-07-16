"""Initialisierung von charakter_daten aus Setting- und Basis-Konfiguration."""

import copy
import json
import re

from app.config import settings

START_ATTRIBUTSTEIGERUNGEN = 5
START_FERTIGKEITSSTEIGERUNGEN = 12

# Mehrfach gewählte Talente legt die Kivy-App als eigene Keys "Name_2" an
_KIVY_KOPIE_RE = re.compile(r"^(.+)_(\d+)$")


def load_setting(setting_name: str) -> dict:
    """Lädt ein Setting — erst die mitgelieferten, dann die eigenen unter
    data/settings (Setting-Verwaltung)."""
    if not setting_name or any(z in setting_name for z in ("/", "\\", "..")):
        raise FileNotFoundError(setting_name)
    for verzeichnis in (settings.gamelogic_path / "settings", settings.custom_settings_path):
        path = verzeichnis / f"{setting_name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(setting_name)


def load_config(name: str) -> dict:
    path = settings.gamelogic_path / "config" / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def baue_attribute(setting: dict, config: dict) -> dict:
    attribute = setting.get("attribute")
    if attribute:
        return copy.deepcopy(attribute)
    # Settings ohne eigene Attribut-Definition (z. B. 50 Fathoms) nutzen den Standard
    return {
        name: {"attribut_name": name, "wert": werte.get("wert", 4), "modifier": werte.get("modifier", 0)}
        for name, werte in config.get("standard_attribute", {}).items()
    }


def baue_fertigkeiten(setting: dict, config: dict) -> dict:
    grundfertigkeiten = set(config.get("grundfertigkeiten", []))
    fertigkeiten = {}
    for name, attribut_liste in setting.get("fertigkeiten_daten", {}).items():
        grund = name in grundfertigkeiten
        fertigkeiten[name] = {
            "fertigkeit_name": name,
            "grundfertigkeit": grund,
            "ausgewaehlt": grund,
            "aktiv": True,
            "wuerfel": {"value": 4, "modifier": 0 if grund else -2, "typ": "fertigkeit"},
            "attribut": attribut_liste[0] if attribut_liste else None,
        }
    return fertigkeiten


def initialisiere_charakter_daten(char_name: str, setting_name: str) -> dict:
    setting = load_setting(setting_name)
    config = load_config("eigenschaften_config.json")

    start_attr = config.get("start_attributsteigerungen", START_ATTRIBUTSTEIGERUNGEN)
    start_fert = config.get("start_fertigkeitssteigerungen", START_FERTIGKEITSSTEIGERUNGEN)

    return {
        "profil_daten": {"Name": char_name},
        "active_setting_name": setting_name,
        "char_gen_completed": False,
        "attribute": baue_attribute(setting, config),
        "fertigkeiten": baue_fertigkeiten(setting, config),
        "selected_handicaps": [],
        "selected_talente": [],
        "selected_maechte": [],
        "voelker_selected": {},
        "ausruestung_selected": {},
        "ausruestung_ausgegeben": 0,
        "startgeld_bonus_punkte": 0,
        "geld_angepasst": 0,
        "cyberware_installationen": {},
        "cyberware_inaktiv": [],
        "cyberware_ausgegeben": 0,
        "cyberware_nebenwirkungen": [],
        "selected_superkraefte": {},
        "verbleibende_attributsteigerungen": start_attr,
        "maximale_attributsteigerungen": start_attr,
        "verbleibende_fertigkeitssteigerungen": start_fert,
        "maximale_fertigkeitssteigerungen": start_fert,
        "gesamt_handicap_punkte": 0,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
        "pathfinder_kostenlose_talente_gewaehlt": 0,
        "aufstiege_gesamt": 0,
        "verbleibende_aufstiege": 0,
    }


def entpacke_charakter_export(daten: dict) -> dict:
    """Packt Voll-Exporte aus, die die eigentlichen charakter_daten in einem
    Wrapper tragen (z. B. DB-Zeilen-Dumps mit id/char_name/benutzername).
    Nackte charakter_daten werden unverändert zurückgegeben."""
    inner = daten.get("charakter_daten")
    if isinstance(inner, dict) and inner:
        return inner
    return daten


def _als_liste(wert) -> list:
    """Kivy-Auswahlen sind je nach Save-Version Skalar oder Liste."""
    if wert is None:
        return []
    if isinstance(wert, list):
        return [w for w in wert if w]
    return [wert]


def _rekonstruiere_volk_effekte(daten: dict, volk_name: str, volk_data: dict, setting: dict) -> dict:
    """Baut das volk_effekte-Tracking für einen Kivy-Alt-Charakter nach.

    Die Effekte selbst (Attribut-Boni, Startfertigkeiten, Auto-Talente, die
    Kern-Wahl wie freies Talent/Attribut und Spezial-Wahlen) sind in den
    exportierten Werten bereits enthalten — hier werden nur die Snapshots
    rekonstruiert, damit Volk-Wechsel und erneutes Wählen sie exakt
    zurücknehmen können und die Wahl im Völker-Tab angezeigt wird.
    Die getroffenen Wahlen stehen im Kivy-Export in voelker_auswahlen.
    """
    effekte = volk_data.get("effects") or {}
    wm = effekte.get("wahlmoeglichkeiten") or {}
    auswahlen = (daten.get("voelker_auswahlen") or {}).get(volk_name) or {}
    attribute = daten.get("attribute", {})
    tracking: dict = {"attribute": {}, "fertigkeiten": {}, "talente": [], "handicaps": []}

    for attr_name, bonus in (effekte.get("attribute_bonuses") or {}).items():
        if attr_name in attribute:
            tracking["attribute"][attr_name] = bonus
    for fert_name, bonus in (effekte.get("fertigkeits_startboni") or {}).items():
        if fert_name in daten.get("fertigkeiten", {}):
            tracking["fertigkeiten"][fert_name] = {"war_untrainiert": True, "delta": bonus}
    for talent in effekte.get("auto_talente") or []:
        if talent in daten.get("selected_talente", []):
            tracking["talente"].append(talent)
    for handicap in effekte.get("auto_handicaps") or []:
        if handicap in daten.get("selected_handicaps", []):
            tracking["handicaps"].append(handicap)

    # freies_talent (Mensch "Vielseitig") wird nicht pauschal registriert:
    # In der Kivy-App gab es den Vorteil nur über die explizite Wahl in
    # voelker_auswahlen. Steht neben freies_talent eine eigene Kern-Wahl
    # (Savage Pathfinder Mensch: zusätzlich freies Attribut), ist das gewählte
    # Talent ein fester Slot und keine tauschbare Wahl.
    from app.services.volk_effekte import KERN_WAHL_KEYS

    hat_freies_talent = wm.get("freies_talent") or wm.get("freies_anfaenger_talent")
    hat_eigene_kern_wahl = any(wm.get(k) for k in KERN_WAHL_KEYS)
    talent_ist_fester_bonus = hat_freies_talent and hat_eigene_kern_wahl
    if talent_ist_fester_bonus and _als_liste(auswahlen.get("talent")):
        tracking["talent_slots"] = 1

    # Kern-Wahl: Mensch "Vielseitig", Halbelf, freies Attribut/Talent
    wahl = None
    kern = auswahlen.get("vielseitig_wahl") or auswahlen.get("halbelf_wahl")
    if isinstance(kern, str) and kern:
        if kern.startswith("Talent:"):
            wahl = {"typ": "talent"}
        elif "Fertigkeitspunkte" in kern:
            wahl = {"typ": "fertigkeitspunkte"}
        else:
            # z. B. "Geschicklichkeit W6"
            attr_name = kern.split(" W")[0].strip()
            if attr_name in attribute:
                wahl = {"typ": "attribut", "ziel": attr_name, "feld": "wert"}
    if wahl is None:
        attr_ziele = [a for a in _als_liste(auswahlen.get("attribut")) if a in attribute]
        if attr_ziele:
            wahl = {"typ": "attribut", "ziel": attr_ziele[0], "feld": "wert"}
        elif not talent_ist_fester_bonus and _als_liste(auswahlen.get("talent")):
            wahl = {"typ": "talent"}
    if wahl:
        tracking["wahl"] = wahl

    # Spezial-Wahlen (attribut_schwaeche, Fertigkeits-Wahlen, magieaffin)
    wahlen: dict = {}
    malus_ziele = [a for a in _als_liste(auswahlen.get("attribut_malus")) if a in attribute]
    if malus_ziele:
        wahlen["attribut_schwaeche"] = {
            "typ": "attribut_malus",
            "ziel": malus_ziele[0],
            "malus": int(effekte.get("attribut_malus_wert", -2)),
        }
    fert_ziele = [
        f for f in _als_liste(auswahlen.get("fertigkeit")) if f in daten.get("fertigkeiten", {})
    ]
    if fert_ziele:
        # Kivy speichert nur den generischen Typ "fertigkeit" — die Wahl-ID
        # ergibt sich aus den Wahlmöglichkeiten des Volkes
        wahl_id = next(
            (
                wid
                for wid in (
                    "heimlich",
                    "freie_verstandsfertigkeit",
                    "handwerks_wissen",
                    "spezialisierung",
                )
                if wm.get(wid)
            ),
            "spezialisierung",
        )
        wahlen[wahl_id] = {
            "typ": "fertigkeit",
            "ziel": fert_ziele[0],
            "war_untrainiert": True,
            "delta": 2,
        }
    magieaffin = auswahlen.get("magieaffin")
    if isinstance(magieaffin, str) and magieaffin:
        from app.services.volk_wahlen import arkane_fertigkeit_aus_ah

        snapshot: dict = {"typ": "magieaffin", "ah_talent": magieaffin}
        if magieaffin in daten.get("selected_talente", []):
            snapshot["talent_hinzugefuegt"] = True
            # wie im Web-Flow: AH-Talent als Volks-Talent registrieren
            tracking["talente"].append(magieaffin)
        fert_name = arkane_fertigkeit_aus_ah(setting.get("talente", {}).get(magieaffin) or {})
        if fert_name and fert_name in daten.get("fertigkeiten", {}):
            snapshot["fertigkeit"] = fert_name
        wahlen["magieaffin"] = snapshot
    if wahlen:
        tracking["wahlen"] = wahlen

    return tracking


def _migriere_kivy_altformat(daten: dict, setting: dict) -> bool:
    """Migriert Alt-Exporte der Kivy-App aufs Web-Format (in-place).

    - voelker_selected: {volk_name: bool} über alle Völker -> {gewähltes Volk: volk_daten}
    - voelker_auswahlen (freies Talent, Attributswahl, ...) -> volk_effekte-Tracking
    - Ausrüstung: selected_elements.ausruestung / ausruestung_mengen plus
      selected_waffen/-ruestungen/-schilde -> ausruestung_selected
    - vermoegen (Rest-Geld) -> ausruestung_ausgegeben (Web rechnet Budget − Ausgaben)
    """
    geaendert = False

    voelker = daten.get("voelker_selected") or {}
    if any(not isinstance(v, dict) for v in voelker.values()):
        gewaehlt = next((name for name, aktiv in voelker.items() if aktiv), None)
        if gewaehlt:
            daten["voelker_selected"] = {gewaehlt: setting.get("voelker", {}).get(gewaehlt) or {}}
        else:
            daten["voelker_selected"] = {}
        geaendert = True

    # Web-Charaktere bekommen volk_effekte beim Volk-Wählen — fehlt es trotz
    # gewähltem Volk bei einem Kivy-Alt-Charakter (erkennbar an dessen
    # Spezial-Feldern), wird das Tracking aus voelker_auswahlen rekonstruiert
    ist_kivy_export = geaendert or any(
        feld in daten for feld in ("voelker_auswahlen", "selected_elements", "ausruestung_mengen")
    )
    voelker = daten.get("voelker_selected") or {}
    if ist_kivy_export and voelker and "volk_effekte" not in daten:
        volk_name, volk_data = next(iter(voelker.items()))
        if isinstance(volk_data, dict):
            daten["volk_effekte"] = _rekonstruiere_volk_effekte(daten, volk_name, volk_data, setting)
            geaendert = True

    # Talent-Kopien "Name_2" (Kivy-Mehrfachauswahl) auf den Basisnamen
    # zurückführen — das Web führt den Namen mehrfach in selected_talente
    setting_talente = setting.get("talente", {})
    migrierte_talente = []
    for name in daten.get("selected_talente") or []:
        m = _KIVY_KOPIE_RE.match(name)
        if m and name not in setting_talente and m.group(1) in setting_talente:
            migrierte_talente.append(m.group(1))
            geaendert = True
        else:
            migrierte_talente.append(name)
    if migrierte_talente != (daten.get("selected_talente") or []):
        daten["selected_talente"] = migrierte_talente

    # Cyberware: Kivy speichert Installationen als {uuid: Installation-Dict}
    # unter selected_elements.cyberware und führt die Implantate zusätzlich in
    # der Ausrüstungsliste; das Web nutzt {name: anzahl} plus das Kauf-Journal
    # cyberware_ausgegeben. Die Namen werden gemerkt, damit die Implantate
    # unten nicht noch einmal als normale Ausrüstung migriert werden.
    kivy_cyber = (daten.get("selected_elements") or {}).get("cyberware") or {}
    cyber_namen: set = set()
    if kivy_cyber and not daten.get("cyberware_installationen"):
        installationen: dict = {}
        instanzen: list = []
        aktive: set = set()
        cyber_kosten = 0.0
        for inst in kivy_cyber.values():
            name = inst.get("name")
            if not name or not inst.get("installiert", True):
                continue
            installationen[name] = installationen.get(name, 0) + 1
            instanzen.append(inst)
            cyber_kosten += inst.get("kosten", 0) or 0
            if inst.get("aktiv", True):
                aktive.add(name)
        if installationen:
            daten["cyberware_installationen"] = installationen
            # Kivy schaltet pro Instanz, das Web pro Name: inaktiv nur, wenn
            # keine Instanz des Implantats aktiv war
            daten["cyberware_inaktiv"] = sorted(set(installationen) - aktive)
            daten["cyberware_ausgegeben"] = cyber_kosten
            # Effekte stecken bereits in den exportierten Werten — die
            # Snapshots werden rekonstruiert, damit Deinstallation sie
            # exakt zurücknehmen kann
            from app.services.cyberware import rekonstruiere_effekt_snapshots

            effekt_snapshots = rekonstruiere_effekt_snapshots(daten, instanzen)
            if effekt_snapshots:
                daten["cyberware_effekte"] = effekt_snapshots
            cyber_namen = set(installationen)
            geaendert = True

    # Superkräfte: Kivy hält die gewählten Kräfte samt Punkten und
    # Modifikatoren unter selected_elements.superkraefte
    # ({name: {"gewaehlte_kosten": Basis-SKP,
    #          "gewaehlte_modifikatoren": [{"name", "kosten"}]}}),
    # während selected_superkraefte nur die Namensliste trägt. Das Web erwartet
    # selected_superkraefte als {name: {"punkte", "modifikatoren": {mod: kosten}}}
    # und die Machtstufe in superkraft_stufe (im Kivy-Export nur implizit über
    # superkraft_punkte_gesamt). Ohne diese Migration bricht /spiellogik/berechne
    # ab (Liste statt Dict), der Superkräfte-Tab fehlt in der Kopie und die
    # Punkte/Modifikatoren, die den Archetyp definieren, gehen verloren. Wie im
    # Original (models/superkraft.py) sind gewaehlte_kosten die reinen Basis-SKP;
    # die Gesamtkosten ergeben sich aus Basis + Modifikatoren.
    if isinstance(daten.get("selected_superkraefte"), list):
        from app.services.superkraefte import _ZAHL_RE, basis_kosten

        kivy_kraefte = (daten.get("selected_elements") or {}).get("superkraefte") or {}
        krafte = setting.get("krafte", {})

        def _mod_kosten(kosten) -> int:
            if isinstance(kosten, (int, float)):
                return int(kosten)
            treffer = _ZAHL_RE.search(str(kosten or ""))
            return int(treffer.group()) if treffer else 0

        migrierte_kraefte: dict = {}
        for name in daten["selected_superkraefte"]:
            if not isinstance(name, str) or not name:
                continue
            info = kivy_kraefte.get(name) or {}
            modifikatoren = {
                mod["name"]: _mod_kosten(mod.get("kosten"))
                for mod in info.get("gewaehlte_modifikatoren") or []
                if isinstance(mod, dict) and mod.get("name")
            }
            punkte = info.get("gewaehlte_kosten")
            if not isinstance(punkte, int):
                # kein Detail-Eintrag: auf die Basiskosten der Kraft zurückfallen
                punkte = basis_kosten((krafte.get(name) or {}).get("kosten"))
            migrierte_kraefte[name] = {"punkte": punkte, "modifikatoren": modifikatoren}
        daten["selected_superkraefte"] = migrierte_kraefte

        # Machtstufe aus dem Gesamtbudget des Archetyps ableiten (45 SKP -> III)
        if not daten.get("superkraft_stufe"):
            budget = daten.get("superkraft_punkte_gesamt")
            stufe = next(
                (
                    s
                    for s, w in (setting.get("machtstufen") or {}).items()
                    if w.get("superkraftpunkte") == budget
                ),
                None,
            )
            if stufe:
                daten["superkraft_stufe"] = stufe
        geaendert = True

    alt = (daten.get("selected_elements") or {}).get("ausruestung") or {}
    if not alt:
        mengen = daten.get("ausruestung_mengen") or {}
        namen = (
            set(mengen)
            | set(daten.get("selected_allgemeine_ausruestung") or [])
            | set(daten.get("selected_waffen") or [])
            | set(daten.get("selected_ruestungen") or [])
            | set(daten.get("selected_schilde") or [])
        )
        alt = {name: {"anzahl": mengen.get(name, 1)} for name in namen}

    if alt and not daten.get("ausruestung_selected"):
        angelegt_namen = set(daten.get("selected_ruestungen") or []) | set(
            daten.get("selected_schilde") or []
        )
        migriert = {}
        for name, eintrag in alt.items():
            # installierte Implantate leben im Cyberware-System, nicht im Besitz
            if name in cyber_namen:
                continue
            anzahl = eintrag.get("anzahl", 1) or 1
            if eintrag.get("ausgewaehlt", True):
                migriert[name] = {"anzahl": anzahl, "angelegt": name in angelegt_namen}
        if migriert or cyber_namen:
            if migriert:
                daten["ausruestung_selected"] = migriert
            # Kivy speichert das Rest-Vermögen; Web speichert die Ausgaben
            from app.services.ausruestung import startkapital_basis, vermoegen_multiplikator
            from app.services.cyberware import geld_belastung

            basis = startkapital_basis(setting, daten)
            gesamt = basis * vermoegen_multiplikator(daten) + basis * daten.get(
                "startgeld_bonus_punkte", 0
            )
            if isinstance(daten.get("vermoegen"), (int, float)):
                # geld_belastung (Cyberware über dem Cyborg-Budget) wird in
                # /berechne erneut abgezogen — hier gegenrechnen, damit das
                # verfügbare Geld exakt dem Kivy-Vermögen entspricht
                daten["ausruestung_ausgegeben"] = (
                    gesamt - daten["vermoegen"] - geld_belastung(daten, setting)
                )
            else:
                katalog = setting.get("ausruestung", {})
                daten["ausruestung_ausgegeben"] = sum(
                    (katalog.get(name, {}).get("kosten", 0) or 0) * e["anzahl"]
                    for name, e in migriert.items()
                )
            geaendert = True

    return geaendert


def ergaenze_fehlende_eigenschaften(daten: dict) -> tuple[dict, bool]:
    """Füllt bei Bestandscharakteren leere attribute/fertigkeiten und fehlende
    Punkte-Felder nach und migriert Kivy-Alt-Exporte. Gibt (neues Dict,
    wurde_geaendert) zurück."""
    config = load_config("eigenschaften_config.json")
    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}

    neu = copy.deepcopy(daten)
    geaendert = False

    if not neu.get("attribute"):
        neu["attribute"] = baue_attribute(setting, config)
        geaendert = True
    if not neu.get("fertigkeiten"):
        neu["fertigkeiten"] = baue_fertigkeiten(setting, config)
        geaendert = True

    # nach dem Auffüllen, damit die Wahl-Rekonstruktion Attribute/Fertigkeiten
    # validieren kann
    geaendert = _migriere_kivy_altformat(neu, setting) or geaendert

    start_attr = config.get("start_attributsteigerungen", START_ATTRIBUTSTEIGERUNGEN)
    start_fert = config.get("start_fertigkeitssteigerungen", START_FERTIGKEITSSTEIGERUNGEN)
    defaults = {
        "verbleibende_attributsteigerungen": start_attr,
        "maximale_attributsteigerungen": start_attr,
        "verbleibende_fertigkeitssteigerungen": start_fert,
        "maximale_fertigkeitssteigerungen": start_fert,
        "gesamt_handicap_punkte": 0,
        "verbleibende_handicap_punkte": 0,
        "verbleibende_talente": 0,
        "pathfinder_kostenlose_talente_gewaehlt": 0,
        "aufstiege_gesamt": 0,
        "verbleibende_aufstiege": 0,
        "ausruestung_selected": {},
        "ausruestung_ausgegeben": 0,
        "startgeld_bonus_punkte": 0,
        "geld_angepasst": 0,
        "cyberware_installationen": {},
        "cyberware_inaktiv": [],
        "cyberware_ausgegeben": 0,
        "cyberware_nebenwirkungen": [],
        "selected_superkraefte": {},
    }
    for feld, wert in defaults.items():
        if feld not in neu:
            neu[feld] = wert
            geaendert = True

    return neu, geaendert
