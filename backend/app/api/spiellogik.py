from fastapi import APIRouter, HTTPException

from app.schemas.spiellogik import (
    CharakterbogenRequest,
    SettingElementRequest,
    SpiellogikRequest,
    SpiellogikResponse,
)
from app.services.charakter_init import initialisiere_charakter_daten, load_config, load_setting
from app.services.handicap_effekte import wende_handicap_punkte_effekte_an
from app.services.kompatibilitaet import handicap_konflikt, talent_konflikt
from app.services.aufstiege import (
    AUFSTIEG_KOSTEN_ATTRIBUT,
    AUFSTIEG_KOSTEN_FERTIGKEIT,
    AUFSTIEG_KOSTEN_HANDICAP,
    AUFSTIEG_KOSTEN_TALENT,
    charakter_rang,
    rang_erlaubt,
)
from app.services.talent_effekte import (
    entferne_talent_effekte,
    ist_auto_element,
    wende_talent_effekte_an,
)
from app.services.talent_voraussetzungen import (
    RANG_NAMEN,
    macht_kapazitaet,
    pruefe_voraussetzungen,
)
from app.services.ausruestung import (
    gesamtgewicht,
    kaufe_ausruestung,
    panzerung_torso,
    schild_parade,
    setze_angelegt,
    traegt_ruestung,
    traglast_kg,
    verfuegbares_geld,
    verkaufe_ausruestung,
)
from app.services import cyberware, superkraefte
from app.services.charakterbogen import generiere_charakterbogen
from app.services.setting_elemente import (
    loesche_element,
    speichere_element,
    wende_setting_overrides_an,
)
from app.services.statblock import generiere_statblock
from app.services.volk_effekte import wende_volk_an, wende_volk_wahl_an
from app.services.volk_wahlen import wende_volk_spezialwahl_an

router = APIRouter(prefix="/api/spiellogik", tags=["spiellogik"])


def _load_setting(setting_name: str, daten: dict | None = None) -> dict:
    """Lädt das Setting; mit daten werden die Charakter-Overrides angewendet."""
    try:
        setting = load_setting(setting_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_name}' nicht gefunden")
    if daten is not None:
        setting = wende_setting_overrides_an(setting, daten)
    return setting


@router.post("/attribut/steigern", response_model=SpiellogikResponse)
def attribut_steigern(req: SpiellogikRequest):
    daten = req.charakter_daten
    attr_name = req.element_name
    if not attr_name or attr_name not in daten.get("attribute", {}):
        return SpiellogikResponse(success=False, message=f"Attribut '{attr_name}' nicht gefunden")

    # Nach der Erschaffung zahlt eine Attributssteigerung 1 Aufstieg
    abgeschlossen = daten.get("char_gen_completed", False)
    if abgeschlossen:
        if daten.get("verbleibende_aufstiege", 0) < AUFSTIEG_KOSTEN_ATTRIBUT:
            return SpiellogikResponse(
                success=False,
                message="Kein Aufstieg verfügbar (Attribut kostet 1 Aufstieg)",
                charakter_daten=daten,
            )
    elif daten.get("verbleibende_attributsteigerungen", 0) <= 0:
        return SpiellogikResponse(
            success=False,
            message="Keine Attributsteigerungen mehr verfügbar",
            charakter_daten=daten,
        )

    attr = daten["attribute"][attr_name]
    wert = attr.get("wert", 4)
    modifier = attr.get("modifier", 0)

    if wert == 12 and modifier >= 2:
        return SpiellogikResponse(
            success=False,
            message=f"{attr_name} ist bereits auf dem Maximum (W12+2)",
            charakter_daten=daten,
        )

    if wert == 12:
        attr["modifier"] = modifier + 1
    elif wert == 4 and modifier == -2:
        attr["modifier"] = 0
    else:
        attr["wert"] = wert + 2

    if abgeschlossen:
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) - AUFSTIEG_KOSTEN_ATTRIBUT
    else:
        daten["verbleibende_attributsteigerungen"] = daten.get("verbleibende_attributsteigerungen", 0) - 1
    daten["attribute"][attr_name] = attr
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/attribut/senken", response_model=SpiellogikResponse)
def attribut_senken(req: SpiellogikRequest):
    daten = req.charakter_daten
    attr_name = req.element_name
    if not attr_name or attr_name not in daten.get("attribute", {}):
        return SpiellogikResponse(success=False, message=f"Attribut '{attr_name}' nicht gefunden")

    attr = daten["attribute"][attr_name]
    wert = attr.get("wert", 4)
    modifier = attr.get("modifier", 0)
    abgeschlossen = daten.get("char_gen_completed", False)
    max_steig = daten.get("maximale_attributsteigerungen", 5)
    verbleibend = daten.get("verbleibende_attributsteigerungen", 0)

    if wert <= 4 and modifier <= 0:
        return SpiellogikResponse(
            success=False,
            message=f"{attr_name} kann nicht weiter gesenkt werden",
            charakter_daten=daten,
        )

    if not abgeschlossen and verbleibend >= max_steig:
        return SpiellogikResponse(
            success=False,
            message="Keine Steigerungen zum Rückgängigmachen",
            charakter_daten=daten,
        )

    if wert == 12 and modifier > 0:
        attr["modifier"] = modifier - 1
    elif wert > 4:
        attr["wert"] = wert - 2
    else:
        return SpiellogikResponse(success=False, message="Minimum erreicht", charakter_daten=daten)

    if abgeschlossen:
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) + AUFSTIEG_KOSTEN_ATTRIBUT
    else:
        daten["verbleibende_attributsteigerungen"] = verbleibend + 1
    daten["attribute"][attr_name] = attr
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/fertigkeit/steigern", response_model=SpiellogikResponse)
def fertigkeit_steigern(req: SpiellogikRequest):
    daten = req.charakter_daten
    fert_name = req.element_name
    if not fert_name or fert_name not in daten.get("fertigkeiten", {}):
        return SpiellogikResponse(success=False, message=f"Fertigkeit '{fert_name}' nicht gefunden")

    fert = daten["fertigkeiten"][fert_name]
    wuerfel = fert.get("wuerfel", {"value": 4, "modifier": -2})
    wert = wuerfel.get("value", 4)
    modifier = wuerfel.get("modifier", -2)

    attr_name = fert.get("attribut", "")
    attr_wert = daten.get("attribute", {}).get(attr_name, {}).get("wert", 4)

    # Steigerung ÜBER das verknüpfte Attribut kostet das Doppelte —
    # maßgeblich ist der neue Wert, also wert >= attr_wert vor der Steigerung.
    # Der erste Kauf (ungelernt -> W4) kostet immer einfach.
    doppelt = modifier != -2 and wert >= attr_wert

    abgeschlossen = daten.get("char_gen_completed", False)
    basis = AUFSTIEG_KOSTEN_FERTIGKEIT if abgeschlossen else 1
    kosten = basis * 2 if doppelt else basis

    if doppelt and not req.ignoriere_pruefungen:
        einheit = "Aufstiege" if abgeschlossen else "Punkte"
        return SpiellogikResponse(
            success=False,
            message=f"{fert_name} liegt über dem verknüpften Attribut ({attr_name} W{attr_wert}) "
            f"— die Steigerung kostet das Doppelte ({kosten:g} {einheit})",
            bestaetigung_moeglich=True,
            charakter_daten=daten,
        )

    if abgeschlossen:
        verbleibend = daten.get("verbleibende_aufstiege", 0)
        if verbleibend < kosten:
            return SpiellogikResponse(
                success=False,
                message=f"Nicht genug Aufstiege ({kosten:g} benötigt, {verbleibend:g} verfügbar)",
                charakter_daten=daten,
            )
    else:
        verbleibend = daten.get("verbleibende_fertigkeitssteigerungen", 0)
        if verbleibend < kosten:
            return SpiellogikResponse(
                success=False,
                message=f"Nicht genug Punkte ({kosten:g} benötigt, {verbleibend} verfügbar)",
                charakter_daten=daten,
            )

    if modifier == -2:
        wuerfel["modifier"] = 0
    elif wert == 12 and modifier < 2:
        wuerfel["modifier"] = modifier + 1
    elif wert < 12:
        wuerfel["value"] = wert + 2
    else:
        return SpiellogikResponse(success=False, message="Maximum erreicht", charakter_daten=daten)

    fert["wuerfel"] = wuerfel
    fert["ausgewaehlt"] = True
    daten["fertigkeiten"][fert_name] = fert
    if abgeschlossen:
        daten["verbleibende_aufstiege"] = verbleibend - kosten
    else:
        daten["verbleibende_fertigkeitssteigerungen"] = verbleibend - kosten
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/fertigkeit/senken", response_model=SpiellogikResponse)
def fertigkeit_senken(req: SpiellogikRequest):
    daten = req.charakter_daten
    fert_name = req.element_name
    if not fert_name or fert_name not in daten.get("fertigkeiten", {}):
        return SpiellogikResponse(success=False, message=f"Fertigkeit '{fert_name}' nicht gefunden")

    fert = daten["fertigkeiten"][fert_name]
    wuerfel = fert.get("wuerfel", {"value": 4, "modifier": 0})
    wert = wuerfel.get("value", 4)
    modifier = wuerfel.get("modifier", 0)
    grundfertigkeit = fert.get("grundfertigkeit", False)

    min_modifier = 0 if grundfertigkeit else -2
    if wert <= 4 and modifier <= min_modifier:
        return SpiellogikResponse(
            success=False,
            message=f"{fert_name} kann nicht weiter gesenkt werden",
            charakter_daten=daten,
        )

    attr_name = fert.get("attribut", "")
    attr_wert = daten.get("attribute", {}).get(attr_name, {}).get("wert", 4)
    abgeschlossen = daten.get("char_gen_completed", False)
    basis = AUFSTIEG_KOSTEN_FERTIGKEIT if abgeschlossen else 1
    refund = basis * 2 if wert > attr_wert else basis

    if wert == 12 and modifier > 0:
        wuerfel["modifier"] = modifier - 1
    elif wert > 4:
        wuerfel["value"] = wert - 2
    elif wert == 4 and modifier == 0 and not grundfertigkeit:
        wuerfel["modifier"] = -2
        refund = basis
    else:
        return SpiellogikResponse(success=False, message="Minimum erreicht", charakter_daten=daten)

    fert["wuerfel"] = wuerfel
    if wuerfel["value"] == 4 and wuerfel["modifier"] == -2:
        fert["ausgewaehlt"] = False
    daten["fertigkeiten"][fert_name] = fert
    if abgeschlossen:
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) + refund
    else:
        daten["verbleibende_fertigkeitssteigerungen"] = daten.get("verbleibende_fertigkeitssteigerungen", 0) + refund
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/handicap/waehlen", response_model=SpiellogikResponse)
def handicap_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    handicap_name = req.element_name
    setting_name = daten.get("active_setting_name", "SWAE")

    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    handicap_data = setting.get("handicaps", {}).get(handicap_name)
    if not handicap_data:
        return SpiellogikResponse(success=False, message=f"Handicap '{handicap_name}' nicht gefunden")

    selected = daten.get("selected_handicaps", [])
    if handicap_name in selected:
        return SpiellogikResponse(success=False, message=f"'{handicap_name}' bereits ausgewählt")

    konflikt = handicap_konflikt(handicap_name, daten)
    if konflikt:
        return SpiellogikResponse(success=False, message=konflikt)

    stufe = handicap_data.get("stufe", "leicht").lower()
    punkte = 1 if stufe == "leicht" else 2
    gesamt = daten.get("gesamt_handicap_punkte", 0)
    if gesamt + punkte > 4:
        return SpiellogikResponse(success=False, message="Maximale Handicap-Punkte (4) erreicht")

    selected.append(handicap_name)
    daten["selected_handicaps"] = selected
    daten["gesamt_handicap_punkte"] = gesamt + punkte
    daten["verbleibende_handicap_punkte"] = daten.get("verbleibende_handicap_punkte", 0) + punkte
    # Spezialeffekte wie "Alt" (+5 Fertigkeitspunkte) oder "Jung" (weniger Steigerungen)
    wende_handicap_punkte_effekte_an(daten, handicap_name, stufe)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/handicap/entfernen", response_model=SpiellogikResponse)
def handicap_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    handicap_name = req.element_name
    selected = daten.get("selected_handicaps", [])

    if handicap_name not in selected:
        return SpiellogikResponse(success=False, message=f"'{handicap_name}' ist nicht ausgewählt")

    if handicap_name in daten.get("volk_effekte", {}).get("handicaps", []):
        return SpiellogikResponse(
            success=False,
            message=f"'{handicap_name}' stammt vom gewählten Volk und kann nicht entfernt werden",
        )

    if ist_auto_element(daten, "handicaps", handicap_name):
        return SpiellogikResponse(
            success=False,
            message=f"'{handicap_name}' wurde automatisch durch ein Talent gewährt "
            "und kann nur mit diesem entfernt werden",
        )

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    handicap_data = setting.get("handicaps", {}).get(handicap_name, {})
    stufe = handicap_data.get("stufe", "leicht").lower()
    punkte = 1 if stufe == "leicht" else 2

    # Nach der Erschaffung wird ein Handicap per Aufstieg ganz abgekauft
    # (SWADE-Aufstiegsoption). Die Erschaffungs-Punkte-Buchhaltung bleibt dabei
    # eingefroren; ein schweres Handicap muss zuvor auf leicht reduziert werden.
    if daten.get("char_gen_completed"):
        if stufe == "schwer":
            return SpiellogikResponse(
                success=False,
                message="Schweres Handicap erst auf 'leicht' reduzieren, bevor es ganz abgekauft werden kann",
                charakter_daten=daten,
            )
        if daten.get("verbleibende_aufstiege", 0) < AUFSTIEG_KOSTEN_HANDICAP:
            return SpiellogikResponse(
                success=False,
                message="Kein Aufstieg verfügbar (Handicap abkaufen kostet 1 Aufstieg)",
                charakter_daten=daten,
            )
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) - AUFSTIEG_KOSTEN_HANDICAP
        selected.remove(handicap_name)
        daten["selected_handicaps"] = selected
        return SpiellogikResponse(success=True, charakter_daten=daten)

    if daten.get("verbleibende_handicap_punkte", 0) < punkte:
        return SpiellogikResponse(
            success=False,
            message="Handicap-Punkte bereits ausgegeben — zuerst Einlösungen rückgängig machen",
            charakter_daten=daten,
        )

    selected.remove(handicap_name)
    daten["selected_handicaps"] = selected
    daten["gesamt_handicap_punkte"] = max(0, daten.get("gesamt_handicap_punkte", 0) - punkte)
    daten["verbleibende_handicap_punkte"] = daten.get("verbleibende_handicap_punkte", 0) - punkte
    wende_handicap_punkte_effekte_an(daten, handicap_name, stufe, vorzeichen=-1)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/handicap/reduzieren", response_model=SpiellogikResponse)
def handicap_reduzieren(req: SpiellogikRequest):
    """Reduziert ein schweres Handicap auf sein leichtes Gegenstück.

    Während der Erschaffung sinkt das Handicap-Punkte-Budget um 1 (schwer 2 →
    leicht 1); nach der Erschaffung kostet die Reduzierung 1 Aufstieg (SWADE).
    Original: reduziere_handicap (handicap_funktionen.py).
    """
    daten = req.charakter_daten
    handicap_name = req.element_name
    selected = daten.get("selected_handicaps", [])

    if handicap_name not in selected:
        return SpiellogikResponse(success=False, message=f"'{handicap_name}' ist nicht ausgewählt")

    if handicap_name in daten.get("volk_effekte", {}).get("handicaps", []):
        return SpiellogikResponse(
            success=False,
            message=f"'{handicap_name}' stammt vom gewählten Volk und kann nicht reduziert werden",
        )

    if ist_auto_element(daten, "handicaps", handicap_name):
        return SpiellogikResponse(
            success=False,
            message=f"'{handicap_name}' wurde automatisch durch ein Talent gewährt "
            "und kann nicht reduziert werden",
        )

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    handicaps = setting.get("handicaps", {})
    handicap_data = handicaps.get(handicap_name, {})
    if handicap_data.get("stufe", "leicht").lower() != "schwer":
        return SpiellogikResponse(
            success=False,
            message=f"'{handicap_name}' ist nicht schwer und kann nicht reduziert werden",
        )

    # Leichtes Gegenstück mit gleichem Anzeigenamen suchen (Original-Logik)
    basis_name = handicap_data.get("name", handicap_name)
    leicht_key = next(
        (
            key
            for key, hd in handicaps.items()
            if hd.get("name") == basis_name and str(hd.get("stufe", "")).lower() == "leicht"
        ),
        None,
    )
    if leicht_key is None:
        return SpiellogikResponse(
            success=False,
            message=f"Kein leichtes Gegenstück für '{basis_name}' vorhanden — "
            "das Handicap kann nur ganz abgekauft (entfernt) werden",
        )
    if leicht_key in selected:
        return SpiellogikResponse(
            success=False,
            message=f"'{basis_name}' ist bereits als leichtes Handicap ausgewählt",
        )

    abgeschlossen = daten.get("char_gen_completed", False)
    if abgeschlossen:
        if daten.get("verbleibende_aufstiege", 0) < AUFSTIEG_KOSTEN_HANDICAP:
            return SpiellogikResponse(
                success=False,
                message="Kein Aufstieg verfügbar (Handicap reduzieren kostet 1 Aufstieg)",
                charakter_daten=daten,
            )
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) - AUFSTIEG_KOSTEN_HANDICAP
    else:
        # Differenz schwer (2) → leicht (1); das Budget muss noch frei sein
        differenz = 2 - 1
        if daten.get("verbleibende_handicap_punkte", 0) < differenz:
            return SpiellogikResponse(
                success=False,
                message="Handicap-Punkte bereits ausgegeben — zuerst Einlösungen rückgängig machen",
                charakter_daten=daten,
            )
        daten["gesamt_handicap_punkte"] = max(0, daten.get("gesamt_handicap_punkte", 0) - differenz)
        daten["verbleibende_handicap_punkte"] = daten.get("verbleibende_handicap_punkte", 0) - differenz
        # Spezial-Punkteeffekte umstellen (schwer zurücknehmen, leicht anwenden)
        wende_handicap_punkte_effekte_an(daten, handicap_name, "schwer", vorzeichen=-1)
        wende_handicap_punkte_effekte_an(daten, leicht_key, "leicht")

    selected.remove(handicap_name)
    selected.append(leicht_key)
    daten["selected_handicaps"] = selected
    return SpiellogikResponse(success=True, charakter_daten=daten)


HANDICAP_EINLOESE_KOSTEN = {"attribut": 2, "fertigkeit": 1, "talent": 2, "startgeld": 1}


@router.post("/handicap-punkte/einloesen", response_model=SpiellogikResponse)
def handicap_punkte_einloesen(req: SpiellogikRequest):
    daten = req.charakter_daten
    option = req.element_name or ""
    kosten = HANDICAP_EINLOESE_KOSTEN.get(option)
    if kosten is None:
        return SpiellogikResponse(
            success=False,
            message=f"Unbekannte Einlöse-Option '{option}' (gültig: attribut, fertigkeit, talent, startgeld)",
        )

    verbleibend = daten.get("verbleibende_handicap_punkte", 0)
    if verbleibend < kosten:
        return SpiellogikResponse(
            success=False,
            message=f"Nicht genug Handicap-Punkte ({kosten} benötigt, {verbleibend} verfügbar)",
            charakter_daten=daten,
        )

    daten["verbleibende_handicap_punkte"] = verbleibend - kosten
    if option == "talent":
        daten["verbleibende_talente"] = daten.get("verbleibende_talente", 0) + 1
    elif option == "startgeld":
        # 1 Punkt → zusätzliches Geld in Höhe des Startkapitals (SWAE)
        daten["startgeld_bonus_punkte"] = daten.get("startgeld_bonus_punkte", 0) + 1
    else:
        feld = "attributsteigerungen" if option == "attribut" else "fertigkeitssteigerungen"
        daten[f"verbleibende_{feld}"] = daten.get(f"verbleibende_{feld}", 0) + 1
        daten[f"maximale_{feld}"] = daten.get(f"maximale_{feld}", 0) + 1
    return SpiellogikResponse(success=True, charakter_daten=daten)


def _ist_pathfinder_setting(daten: dict) -> bool:
    return "pathfinder" in daten.get("active_setting_name", "").lower()


def _pathfinder_kostenlos_moeglich(daten: dict, talent_data: dict) -> bool:
    """Savage Pathfinder: bei der Erschaffung ist ein Talent der Kategorie
    "Klasse" kostenlos (Original: ist_pathfinder_kostenloses_talent /
    hat_bereits_kostenloses_pathfinder_talent)."""
    if daten.get("char_gen_completed") or not _ist_pathfinder_setting(daten):
        return False
    if talent_data.get("kategorie") != "Klasse":
        return False
    maximum = load_config("talent_config.json").get("kosten", {}).get("pathfinder_max_kostenlose", 1)
    return daten.get("pathfinder_kostenlose_talente_gewaehlt", 0) < maximum


def _ist_talent_duplizierbar(talent_name: str, talent_data: dict) -> bool:
    """Mehrfachauswahl wie im Original: erlaubt (z. B. "Neue Mächte",
    "Machtpunkte", "Anhänger"), außer das Talent steht in der Sperrliste
    nicht_duplizierbare_talente der talent_config.json."""
    gesperrt = load_config("talent_config.json").get("nicht_duplizierbare_talente", [])
    return talent_name not in gesperrt and talent_data.get("name", talent_name) not in gesperrt


@router.post("/talent/waehlen", response_model=SpiellogikResponse)
def talent_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    talent_name = req.element_name
    selected = daten.get("selected_talente", [])

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting_talente = _load_setting(setting_name, daten).get("talente", {})
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    talent_data = setting_talente.get(talent_name)
    if not talent_data:
        return SpiellogikResponse(success=False, message=f"Talent '{talent_name}' nicht gefunden")

    if talent_name in selected and not _ist_talent_duplizierbar(talent_name, talent_data):
        return SpiellogikResponse(
            success=False, message=f"'{talent_name}' kann nicht mehrfach ausgewählt werden"
        )

    # Rang-Gate gegen den Charakterrang (aus ausgegebenen Aufstiegen; bei der
    # Erschaffung Anfänger); wie im Original per Bestätigung überspringbar
    rang = talent_data.get("rang", "A")
    if not rang_erlaubt(rang, daten) and not req.ignoriere_pruefungen:
        return SpiellogikResponse(
            success=False,
            message=f"'{talent_name}' erfordert Rang {RANG_NAMEN.get(rang, rang)} — "
            f"der Charakter ist {charakter_rang(daten)}",
            bestaetigung_moeglich=True,
        )

    fehlend = pruefe_voraussetzungen(talent_data, daten, setting_talente)
    if fehlend and not req.ignoriere_pruefungen:
        return SpiellogikResponse(
            success=False,
            message=f"Voraussetzungen nicht erfüllt: {', '.join(fehlend)}",
            bestaetigung_moeglich=True,
        )

    # Verbotene Kombinationen (z. B. Reich + Arm) sind nicht überspringbar
    konflikt = talent_konflikt(talent_name, daten)
    if konflikt:
        return SpiellogikResponse(success=False, message=konflikt)

    # Bezahlung wie im Original: erst das kostenlose Pathfinder-Klassen-Talent,
    # dann freie Slots (Volks-Talent, eingelöste Punkte); während der
    # Erschaffung sonst 2 Handicap-Punkte, danach 1 Aufstieg
    talent_kosten = HANDICAP_EINLOESE_KOSTEN["talent"]
    abgeschlossen = daten.get("char_gen_completed", False)
    erfolgsmeldung = ""
    if _pathfinder_kostenlos_moeglich(daten, talent_data):
        zahlungsquelle = "pathfinder_kostenlos"
        daten["pathfinder_kostenlose_talente_gewaehlt"] = (
            daten.get("pathfinder_kostenlose_talente_gewaehlt", 0) + 1
        )
        erfolgsmeldung = f"'{talent_name}' als kostenloses Klassen-Talent gewählt (Savage Pathfinder)"
    elif daten.get("verbleibende_talente", 0) > 0:
        zahlungsquelle = "slot"
        daten["verbleibende_talente"] = daten["verbleibende_talente"] - 1
    elif not abgeschlossen and daten.get("verbleibende_handicap_punkte", 0) >= talent_kosten:
        zahlungsquelle = "handicap_punkte"
        daten["verbleibende_handicap_punkte"] = daten["verbleibende_handicap_punkte"] - talent_kosten
    elif abgeschlossen and daten.get("verbleibende_aufstiege", 0) >= AUFSTIEG_KOSTEN_TALENT:
        zahlungsquelle = "aufstieg"
        daten["verbleibende_aufstiege"] = daten["verbleibende_aufstiege"] - AUFSTIEG_KOSTEN_TALENT
    elif abgeschlossen:
        return SpiellogikResponse(
            success=False,
            message="Kein Aufstieg verfügbar (Talent kostet 1 Aufstieg)",
            charakter_daten=daten,
        )
    else:
        return SpiellogikResponse(
            success=False,
            message=f"Kein Talent-Slot und keine {talent_kosten} Handicap-Punkte verfügbar — "
            "Handicaps wählen (max. 4 Punkte) oder ein Volk mit freiem Talent",
            charakter_daten=daten,
        )

    selected.append(talent_name)
    daten["selected_talente"] = selected
    # Zahlungsquelle je Kopie (Altbestand: einzelner String statt Liste)
    zahlungen = daten.setdefault("talent_zahlungen", {})
    bisherige = zahlungen.get(talent_name)
    bisherige = [bisherige] if isinstance(bisherige, str) else list(bisherige or [])
    zahlungen[talent_name] = bisherige + [zahlungsquelle]
    # Auto-Handicaps/-Talente/-Mächte und Attribut-Effekte (z. B. Berserker)
    wende_talent_effekte_an(daten, talent_name, talent_data)
    return SpiellogikResponse(success=True, message=erfolgsmeldung, charakter_daten=daten)


def _kivy_import_zahlungsquelle(daten: dict, talent_name: str) -> str:
    """Zahlungsquelle für Talente ohne Zahlungsjournal (Kivy-Importe).

    Wie das Original beim Abwählen: ein Klassen-Talent gibt zuerst das
    kostenlose Pathfinder-Talent frei, sonst wird ein Slot erstattet."""
    if _ist_pathfinder_setting(daten) and daten.get("pathfinder_kostenlose_talente_gewaehlt", 0) > 0:
        try:
            setting = _load_setting(daten.get("active_setting_name", "SWAE"), daten)
        except HTTPException:
            return "slot"
        talent_data = setting.get("talente", {}).get(talent_name) or {}
        if talent_data.get("kategorie") == "Klasse":
            return "pathfinder_kostenlos"
    return "slot"


@router.post("/talent/entfernen", response_model=SpiellogikResponse)
def talent_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    talent_name = req.element_name
    selected = daten.get("selected_talente", [])

    if talent_name not in selected:
        return SpiellogikResponse(success=False, message=f"'{talent_name}' ist nicht ausgewählt")

    # Volk-/Auto-Kopien sind einzeln — bei Mehrfachauswahl wird zuerst die
    # dazugekaufte Kopie entfernt, nur die letzte ist geschützt
    letzte_kopie = selected.count(talent_name) == 1

    if letzte_kopie and talent_name in daten.get("volk_effekte", {}).get("talente", []):
        return SpiellogikResponse(
            success=False,
            message=f"'{talent_name}' stammt vom gewählten Volk und kann nicht entfernt werden",
        )

    if letzte_kopie and ist_auto_element(daten, "talente", talent_name):
        return SpiellogikResponse(
            success=False,
            message=f"'{talent_name}' wurde automatisch durch ein anderes Talent gewährt "
            "und kann nur mit diesem entfernt werden",
        )

    selected.remove(talent_name)
    daten["selected_talente"] = selected
    # Erstattung an die zuletzt genutzte Zahlungsquelle (Altbestand: String)
    zahlungen = daten.setdefault("talent_zahlungen", {})
    quellen = zahlungen.get(talent_name)
    quellen = [quellen] if isinstance(quellen, str) else list(quellen or [])
    quelle = quellen.pop() if quellen else _kivy_import_zahlungsquelle(daten, talent_name)
    if quellen:
        zahlungen[talent_name] = quellen
    else:
        zahlungen.pop(talent_name, None)
    if quelle == "pathfinder_kostenlos":
        # Original: Zähler freigeben, keine Slot-/Punkte-Erstattung
        daten["pathfinder_kostenlose_talente_gewaehlt"] = max(
            0, daten.get("pathfinder_kostenlose_talente_gewaehlt", 0) - 1
        )
    elif quelle == "handicap_punkte":
        daten["verbleibende_handicap_punkte"] = (
            daten.get("verbleibende_handicap_punkte", 0) + HANDICAP_EINLOESE_KOSTEN["talent"]
        )
    elif quelle == "aufstieg":
        daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) + AUFSTIEG_KOSTEN_TALENT
    else:
        daten["verbleibende_talente"] = daten.get("verbleibende_talente", 0) + 1
    entferne_talent_effekte(daten, talent_name)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/macht/waehlen", response_model=SpiellogikResponse)
def macht_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    macht_name = req.element_name
    selected = daten.get("selected_maechte", [])

    if macht_name in selected:
        return SpiellogikResponse(success=False, message=f"'{macht_name}' bereits ausgewählt")

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    macht_data = setting.get("maechte", {}).get(macht_name)
    if not macht_data:
        return SpiellogikResponse(success=False, message=f"Macht '{macht_name}' nicht gefunden")

    rang = macht_data.get("rang", "A")
    if not rang_erlaubt(rang, daten) and not req.ignoriere_pruefungen:
        return SpiellogikResponse(
            success=False,
            message=f"'{macht_name}' erfordert Rang {RANG_NAMEN.get(rang, rang)} — "
            f"der Charakter ist {charakter_rang(daten)}",
            bestaetigung_moeglich=True,
        )

    slots, _ = macht_kapazitaet(daten, setting.get("talente", {}))
    if slots == 0:
        return SpiellogikResponse(
            success=False,
            message="Kein arkaner Hintergrund — zuerst ein AH-Talent wählen",
        )
    if len(selected) >= slots:
        return SpiellogikResponse(
            success=False,
            message=f"Alle Mächte-Slots belegt ({slots}) — z. B. Talent 'Neue Mächte' wählen",
            charakter_daten=daten,
        )

    selected.append(macht_name)
    daten["selected_maechte"] = selected
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/macht/entfernen", response_model=SpiellogikResponse)
def macht_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    macht_name = req.element_name
    selected = daten.get("selected_maechte", [])

    if macht_name not in selected:
        return SpiellogikResponse(success=False, message=f"'{macht_name}' ist nicht ausgewählt")

    if ist_auto_element(daten, "maechte", macht_name):
        return SpiellogikResponse(
            success=False,
            message=f"'{macht_name}' wurde automatisch durch ein Talent gewährt "
            "und kann nur mit diesem entfernt werden",
        )

    selected.remove(macht_name)
    daten["selected_maechte"] = selected
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/erschaffung/abschliessen", response_model=SpiellogikResponse)
def erschaffung_abschliessen(req: SpiellogikRequest):
    daten = req.charakter_daten
    if daten.get("char_gen_completed"):
        return SpiellogikResponse(
            success=False, message="Erschaffung ist bereits abgeschlossen", charakter_daten=daten
        )
    # Original: nur ein Hinweis, das Abschließen bleibt möglich
    hinweis = ""
    if _ist_pathfinder_setting(daten) and not daten.get("pathfinder_kostenlose_talente_gewaehlt", 0):
        hinweis = " — Hinweis: das kostenlose Klassen-Talent (Savage Pathfinder) wurde nicht gewählt"
    daten["char_gen_completed"] = True
    return SpiellogikResponse(
        success=True,
        message="Erschaffung abgeschlossen — weitere Steigerungen kosten Aufstiege" + hinweis,
        charakter_daten=daten,
    )


@router.post("/erschaffung/oeffnen", response_model=SpiellogikResponse)
def erschaffung_oeffnen(req: SpiellogikRequest):
    daten = req.charakter_daten
    if not daten.get("char_gen_completed"):
        return SpiellogikResponse(
            success=False, message="Erschaffung ist noch nicht abgeschlossen", charakter_daten=daten
        )
    daten["char_gen_completed"] = False
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/aufstieg/hinzufuegen", response_model=SpiellogikResponse)
def aufstieg_hinzufuegen(req: SpiellogikRequest):
    daten = req.charakter_daten
    if not daten.get("char_gen_completed"):
        return SpiellogikResponse(
            success=False,
            message="Aufstiege gibt es erst nach Abschluss der Erschaffung",
            charakter_daten=daten,
        )
    daten["aufstiege_gesamt"] = daten.get("aufstiege_gesamt", 0) + 1
    daten["verbleibende_aufstiege"] = daten.get("verbleibende_aufstiege", 0) + 1
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/aufstieg/entfernen", response_model=SpiellogikResponse)
def aufstieg_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    if daten.get("aufstiege_gesamt", 0) <= 0:
        return SpiellogikResponse(success=False, message="Keine Aufstiege vorhanden", charakter_daten=daten)
    if daten.get("verbleibende_aufstiege", 0) < 1:
        return SpiellogikResponse(
            success=False,
            message="Aufstieg bereits ausgegeben — zuerst Steigerungen zurücknehmen",
            charakter_daten=daten,
        )
    daten["aufstiege_gesamt"] = daten["aufstiege_gesamt"] - 1
    daten["verbleibende_aufstiege"] = daten["verbleibende_aufstiege"] - 1
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/setting/wechseln", response_model=SpiellogikResponse)
def setting_wechseln(req: SpiellogikRequest):
    daten = req.charakter_daten
    neues_setting = req.element_name or ""

    if neues_setting == daten.get("active_setting_name"):
        return SpiellogikResponse(
            success=False,
            message=f"Setting '{neues_setting}' ist bereits aktiv",
            charakter_daten=daten,
        )

    char_name = daten.get("profil_daten", {}).get("Name", "")
    try:
        neu = initialisiere_charakter_daten(char_name, neues_setting)
    except FileNotFoundError:
        return SpiellogikResponse(success=False, message=f"Setting '{neues_setting}' nicht gefunden")

    # Profil bleibt erhalten, alles Settingspezifische (Attribute, Fertigkeiten,
    # Selektionen, Punkte) wird neu aufgebaut
    neu["profil_daten"] = daten.get("profil_daten", neu["profil_daten"])
    return SpiellogikResponse(
        success=True,
        message=f"Setting gewechselt zu '{neues_setting}' — Eigenschaften und Auswahl wurden zurückgesetzt",
        charakter_daten=neu,
    )


@router.post("/volk/waehlen", response_model=SpiellogikResponse)
def volk_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    volk_name = req.element_name
    setting_name = daten.get("active_setting_name", "SWAE")

    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    volk_data = setting.get("voelker", {}).get(volk_name)
    if not volk_data:
        return SpiellogikResponse(success=False, message=f"Volk '{volk_name}' nicht gefunden")

    daten = wende_volk_an(daten, volk_name, volk_data)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/volk/wahl", response_model=SpiellogikResponse)
def volk_wahl(req: SpiellogikRequest):
    """Löst eine Wahlmöglichkeit des gewählten Volkes ein.

    Kern-Wahl (z. B. Halbelf: freies Talent ODER Attribut): element_name ist
    "talent", "fertigkeitspunkte" oder ein Attributname. Spezial-Wahlen
    (heimlich, magieaffin, attribut_schwaeche, ...) nutzen das Format
    "wahl_id:auswahl", z. B. "heimlich:Diebeskunst" oder
    "magieaffin:AH (Magie)"."""
    daten = req.charakter_daten
    element = req.element_name or ""
    wahl_id, sep, auswahl = element.partition(":")
    if sep:
        setting_name = daten.get("active_setting_name", "SWAE")
        try:
            setting = _load_setting(setting_name, daten)
        except HTTPException:
            return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")
        ok, message = wende_volk_spezialwahl_an(daten, setting, wahl_id.strip(), auswahl.strip())
    else:
        ok, message = wende_volk_wahl_an(daten, element)
    if not ok:
        return SpiellogikResponse(success=False, message=message, charakter_daten=daten)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/ausruestung/kaufen", response_model=SpiellogikResponse)
def ausruestung_kaufen(req: SpiellogikRequest):
    daten = req.charakter_daten
    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")
    ok, message = kaufe_ausruestung(daten, setting, req.element_name or "")
    return SpiellogikResponse(success=ok, message=message, charakter_daten=daten)


@router.post("/ausruestung/verkaufen", response_model=SpiellogikResponse)
def ausruestung_verkaufen(req: SpiellogikRequest):
    daten = req.charakter_daten
    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")
    ok, message = verkaufe_ausruestung(daten, setting, req.element_name or "")
    return SpiellogikResponse(success=ok, message=message, charakter_daten=daten)


@router.post("/ausruestung/anlegen", response_model=SpiellogikResponse)
def ausruestung_anlegen(req: SpiellogikRequest):
    return _ausruestung_angelegt(req, True)


@router.post("/ausruestung/ablegen", response_model=SpiellogikResponse)
def ausruestung_ablegen(req: SpiellogikRequest):
    return _ausruestung_angelegt(req, False)


def _ausruestung_angelegt(req: SpiellogikRequest, angelegt: bool) -> SpiellogikResponse:
    daten = req.charakter_daten
    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")
    ok, message = setze_angelegt(daten, setting, req.element_name or "", angelegt)
    return SpiellogikResponse(success=ok, message=message, charakter_daten=daten)


def _mit_setting(req: SpiellogikRequest, aktion) -> SpiellogikResponse:
    """Führt aktion(daten, setting, element) aus; lädt vorher das Setting."""
    daten = req.charakter_daten
    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name, daten)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")
    ok, message = aktion(daten, setting, req.element_name or "")
    return SpiellogikResponse(success=ok, message=message, charakter_daten=daten)


@router.post("/cyberware/installieren", response_model=SpiellogikResponse)
def cyberware_installieren(req: SpiellogikRequest):
    def aktion(daten, setting, element):
        geld, _ = verfuegbares_geld(daten, setting)
        return cyberware.installiere(daten, setting, element, geld)

    return _mit_setting(req, aktion)


@router.post("/cyberware/deinstallieren", response_model=SpiellogikResponse)
def cyberware_deinstallieren(req: SpiellogikRequest):
    return _mit_setting(req, lambda d, s, e: cyberware.deinstalliere(d, s, e))


@router.post("/cyberware/nebenwirkung", response_model=SpiellogikResponse)
def cyberware_nebenwirkung(req: SpiellogikRequest):
    return _mit_setting(req, lambda d, s, e: cyberware.wuerfle_nebenwirkung(d, s))


@router.post("/cyberware/nebenwirkung-entfernen", response_model=SpiellogikResponse)
def cyberware_nebenwirkung_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    liste = daten.get("cyberware_nebenwirkungen", [])
    try:
        index = int(req.element_name or "")
        liste.pop(index)
    except (ValueError, IndexError):
        return SpiellogikResponse(success=False, message="Ungültiger Nebenwirkungs-Index", charakter_daten=daten)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/superkraft/stufe", response_model=SpiellogikResponse)
def superkraft_stufe(req: SpiellogikRequest):
    return _mit_setting(req, lambda d, s, e: superkraefte.setze_machtstufe(d, s, e))


@router.post("/superkraft/waehlen", response_model=SpiellogikResponse)
def superkraft_waehlen(req: SpiellogikRequest):
    return _mit_setting(req, lambda d, s, e: superkraefte.waehle_kraft(d, s, e))


@router.post("/superkraft/entfernen", response_model=SpiellogikResponse)
def superkraft_entfernen(req: SpiellogikRequest):
    return _mit_setting(req, lambda d, s, e: superkraefte.entferne_kraft(d, e))


@router.post("/superkraft/punkte", response_model=SpiellogikResponse)
def superkraft_punkte(req: SpiellogikRequest):
    """element_name: "Kraftname:Punkte", z. B. "Fliegen:8"."""

    def aktion(daten, setting, element):
        name, sep, punkte = element.rpartition(":")
        if not sep or not punkte.lstrip("-").isdigit():
            return False, 'Format: "Kraftname:Punkte"'
        return superkraefte.setze_punkte(daten, setting, name.strip(), int(punkte))

    return _mit_setting(req, aktion)


@router.post("/superkraft/modifikator", response_model=SpiellogikResponse)
def superkraft_modifikator(req: SpiellogikRequest):
    """element_name: "Kraftname:Modifikator" — wählt ab oder an (Toggle)."""

    def aktion(daten, setting, element):
        name, sep, mod = element.partition(":")
        if not sep or not mod.strip():
            return False, 'Format: "Kraftname:Modifikator"'
        return superkraefte.toggle_modifikator(daten, setting, name.strip(), mod.strip())

    return _mit_setting(req, aktion)


_BERECHNE_STATS = ("parade", "robustheit", "bewegungsweite", "groesse", "bennys", "traglast_kg", "panzerung")


def _sammle_effekt_boni(daten: dict, setting: dict) -> dict:
    """Summiert Boni aus Talenten, Handicaps (abgeleitete_effekte.json) und Volk."""
    cfg = load_config("abgeleitete_effekte.json")
    boni = {stat: 0 for stat in _BERECHNE_STATS}

    # Talente: additiv; innerhalb einer nicht_kumulativ_gruppe zählt nur das Maximum
    gruppen: dict[str, dict[str, int]] = {}
    for talent in daten.get("selected_talente", []):
        effekt = cfg.get("talente", {}).get(talent)
        if not effekt:
            continue
        effekt = dict(effekt)
        gruppe = effekt.pop("nicht_kumulativ_gruppe", None)
        bedingung = effekt.pop("bedingung", None)
        if bedingung == "keine_getragene_ruestung" and traegt_ruestung(daten, setting):
            continue
        ziel = gruppen.setdefault(gruppe, {}) if gruppe else None
        for stat, wert in effekt.items():
            if stat not in boni:
                continue
            if ziel is not None:
                ziel[stat] = max(ziel.get(stat, 0), wert)
            else:
                boni[stat] += wert
    for gruppe_boni in gruppen.values():
        for stat, wert in gruppe_boni.items():
            boni[stat] += wert

    # Handicaps: Lookup über Stufe aus dem Setting (oder alle_stufen)
    setting_handicaps = setting.get("handicaps", {})
    for handicap in daten.get("selected_handicaps", []):
        # Setting-Namen tragen die Stufe teils als Suffix ("Langsam_leicht"),
        # die Effekt-Config führt den Basisnamen mit Stufen-Keys
        basis, stufe = handicap, None
        if handicap.endswith(("_leicht", "_schwer")):
            basis, stufe = handicap[:-7], handicap[-6:]
        stufen_effekte = cfg.get("handicaps", {}).get(basis)
        if not stufen_effekte:
            continue
        if stufe is None:
            stufe = setting_handicaps.get(handicap, {}).get("stufe", "leicht").lower()
        effekt = stufen_effekte.get(stufe) or stufen_effekte.get("alle_stufen") or {}
        for stat, wert in effekt.items():
            if stat in boni:
                boni[stat] += wert

    # Volk: Boni stehen strukturiert im effects-Objekt des gewählten Volkes.
    # Alt-Format aus der Kivy-App speichert {volk_name: bool} statt Volk-Daten.
    for volk_data in daten.get("voelker_selected", {}).values():
        if not isinstance(volk_data, dict):
            continue
        effekte = volk_data.get("effects") or {}
        boni["bewegungsweite"] += effekte.get("bewegungsweite_bonus", 0)
        boni["robustheit"] += effekte.get("robustheit_bonus", 0)
        boni["groesse"] += effekte.get("groesse_modifikator", 0)
        boni["parade"] += effekte.get("parade_bonus", 0)
        boni["panzerung"] += effekte.get("panzerung_bonus", 0)

    return boni


@router.post("/berechne")
def berechne_abgeleitete_werte(req: SpiellogikRequest):
    daten = req.charakter_daten

    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}
    setting = wende_setting_overrides_an(setting, daten)

    kon_wert = daten.get("attribute", {}).get("Konstitution", {}).get("wert", 4)
    kaempfen = daten.get("fertigkeiten", {}).get("Kämpfen", {})
    kaempfen_wuerfel = kaempfen.get("wuerfel", {"value": 4, "modifier": -2})
    kaempfen_ungelernt = kaempfen_wuerfel.get("modifier", 0) == -2
    kaempfen_wert = 0 if kaempfen_ungelernt else kaempfen_wuerfel.get("value", 4)

    boni = _sammle_effekt_boni(daten, setting)
    macht_slots, machtpunkte = macht_kapazitaet(daten, setting.get("talente", {}))
    # Volks-Mächte (Eigenart "Macht" einer eigenen Abstammung) belegen eigene Slots
    for volk_data in daten.get("voelker_selected", {}).values():
        if isinstance(volk_data, dict):
            macht_slots += len((volk_data.get("effects") or {}).get("auto_maechte") or [])

    cyber_aktiv = cyberware.ist_cyberware_setting(daten.get("active_setting_name", ""))
    cyber_boni = (
        cyberware.stat_boni(daten, setting)
        if cyber_aktiv
        else {"robustheit": 0, "bewegungsweite": 0, "groesse": 0, "panzerung": 0}
    )

    groesse = boni["groesse"] + cyber_boni["groesse"]
    panzerung = panzerung_torso(daten, setting) + cyber_boni["panzerung"] + boni["panzerung"]
    parade = 2 + (kaempfen_wert // 2) + boni["parade"] + schild_parade(daten, setting)
    # Größe und Torso-Panzerung fließen nach SWAE in die Robustheit ein
    robustheit = 2 + (kon_wert // 2) + boni["robustheit"] + cyber_boni["robustheit"] + groesse + panzerung
    bewegungsweite = 6 + boni["bewegungsweite"] + cyber_boni["bewegungsweite"]
    bennys = 3 + boni["bennys"]
    geld_verfuegbar, geld_gesamt = verfuegbares_geld(daten, setting)

    extra: dict = {}
    if cyber_aktiv:
        aktuell = cyberware.stress_aktuell(daten, setting)
        limit = cyberware.stresslimit(daten, setting)
        extra["cyberware"] = {
            "stress": aktuell,
            "stresslimit": limit,
            "stress_maximum": cyberware.stress_maximum(daten, setting),
            "ueber_limit": max(0, aktuell - limit),
        }
    if superkraefte.ist_superkraefte_setting(setting):
        budget = superkraefte.skp_budget(daten, setting)
        ausgegeben = superkraefte.skp_ausgegeben(daten)
        extra["superkraefte"] = {
            "stufe": daten.get("superkraft_stufe", superkraefte.STANDARD_STUFE),
            "budget": budget,
            "ausgegeben": ausgegeben,
            "verbleibend": budget - ausgegeben,
            "kraftobergrenze": superkraefte.kraftobergrenze(daten, setting),
            "talent_gewaehlt": superkraefte.hat_superkraefte_talent(daten),
        }

    return {
        **extra,
        "parade": parade,
        "robustheit": robustheit,
        "bewegungsweite": bewegungsweite,
        "groesse": groesse,
        "bennys": bennys,
        "panzerung": panzerung,
        "vermoegen": geld_verfuegbar,
        "startkapital_gesamt": geld_gesamt,
        "traglast": traglast_kg(daten, boni["traglast_kg"]),
        "gesamtgewicht": gesamtgewicht(daten, setting),
        "machtpunkte": machtpunkte,
        "verbleibende_maechte": max(0, macht_slots - len(daten.get("selected_maechte", []))),
        "verbleibende_attributsteigerungen": daten.get("verbleibende_attributsteigerungen", 5),
        "verbleibende_fertigkeitssteigerungen": daten.get("verbleibende_fertigkeitssteigerungen", 12),
        "verbleibende_handicap_punkte": daten.get("verbleibende_handicap_punkte", 0),
        "verbleibende_talente": daten.get("verbleibende_talente", 0),
        "verbleibende_aufstiege": daten.get("verbleibende_aufstiege", 0),
        "aufstiege_gesamt": daten.get("aufstiege_gesamt", 0),
        "rang": charakter_rang(daten),
    }


@router.post("/statblock")
def statblock(req: SpiellogikRequest):
    """Kompakter Text-Statblock des Charakters (SWADE-Stil, wie im Original)."""
    daten = req.charakter_daten
    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}
    setting = wende_setting_overrides_an(setting, daten)
    werte = berechne_abgeleitete_werte(req)
    return {"statblock": generiere_statblock(daten, setting, werte)}


@router.post("/charakterbogen")
def charakterbogen(req: CharakterbogenRequest):
    """Kompletter Charakterbogen als HTML-Dokument (wie im Original)."""
    daten = req.charakter_daten
    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}
    setting = wende_setting_overrides_an(setting, daten)
    werte = berechne_abgeleitete_werte(req)
    return {"html": generiere_charakterbogen(daten, setting, werte, req.printer_friendly)}


@router.post("/talente/verfuegbar")
def talente_verfuegbar(req: SpiellogikRequest):
    """Namen aller Talente, deren Rang und Voraussetzungen der Charakter
    aktuell erfüllt (Original: Filter "Nur verfügbare Talente")."""
    daten = req.charakter_daten
    setting = _load_setting(daten.get("active_setting_name", "SWAE"), daten)
    setting_talente = setting.get("talente", {})
    verfuegbar = [
        name
        for name, talent in setting_talente.items()
        if rang_erlaubt(talent.get("rang", "A"), daten)
        and not pruefe_voraussetzungen(talent, daten, setting_talente)
    ]
    return {"verfuegbar": verfuegbar}


@router.post("/element/speichern", response_model=SpiellogikResponse)
def element_speichern(req: SettingElementRequest):
    """Legt ein Setting-Element an oder bearbeitet es (Original: Element-Popups).

    Die Änderung landet in charakter_daten["setting_overrides"] und gilt nur
    für diesen Charakter."""
    daten = req.charakter_daten
    setting = _load_setting(daten.get("active_setting_name", "SWAE"))
    ok, meldung = speichere_element(
        daten, setting, req.element_typ, req.element_name or "", req.element_daten or {}, req.alter_name
    )
    if not ok:
        return SpiellogikResponse(success=False, message=meldung)
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/element/loeschen", response_model=SpiellogikResponse)
def element_loeschen(req: SettingElementRequest):
    """Entfernt ein Setting-Element für diesen Charakter (native Elemente
    werden über die geloescht-Liste ausgeblendet, eigene ganz entfernt)."""
    daten = req.charakter_daten
    setting = _load_setting(daten.get("active_setting_name", "SWAE"))
    ok, meldung = loesche_element(daten, setting, req.element_typ, req.element_name or "")
    if not ok:
        return SpiellogikResponse(success=False, message=meldung)
    return SpiellogikResponse(success=True, charakter_daten=daten)
