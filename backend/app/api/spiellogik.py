from fastapi import APIRouter, HTTPException

from app.schemas.spiellogik import SpiellogikRequest, SpiellogikResponse
from app.services.charakter_init import initialisiere_charakter_daten, load_config, load_setting
from app.services.talent_voraussetzungen import (
    RANG_NAMEN,
    macht_kapazitaet,
    pruefe_voraussetzungen,
)
from app.services.volk_effekte import wende_volk_an

router = APIRouter(prefix="/api/spiellogik", tags=["spiellogik"])


def _load_setting(setting_name: str) -> dict:
    try:
        return load_setting(setting_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_name}' nicht gefunden")


@router.post("/attribut/steigern", response_model=SpiellogikResponse)
def attribut_steigern(req: SpiellogikRequest):
    daten = req.charakter_daten
    attr_name = req.element_name
    if not attr_name or attr_name not in daten.get("attribute", {}):
        return SpiellogikResponse(success=False, message=f"Attribut '{attr_name}' nicht gefunden")

    verbleibend = daten.get("verbleibende_attributsteigerungen", 0)
    if verbleibend <= 0:
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

    daten["verbleibende_attributsteigerungen"] = verbleibend - 1
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
    max_steig = daten.get("maximale_attributsteigerungen", 5)
    verbleibend = daten.get("verbleibende_attributsteigerungen", 0)

    if wert <= 4 and modifier <= 0:
        return SpiellogikResponse(
            success=False,
            message=f"{attr_name} kann nicht weiter gesenkt werden",
            charakter_daten=daten,
        )

    if verbleibend >= max_steig:
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

    daten["verbleibende_attributsteigerungen"] = verbleibend + 1
    daten["attribute"][attr_name] = attr
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/fertigkeit/steigern", response_model=SpiellogikResponse)
def fertigkeit_steigern(req: SpiellogikRequest):
    daten = req.charakter_daten
    fert_name = req.element_name
    if not fert_name or fert_name not in daten.get("fertigkeiten", {}):
        return SpiellogikResponse(success=False, message=f"Fertigkeit '{fert_name}' nicht gefunden")

    verbleibend = daten.get("verbleibende_fertigkeitssteigerungen", 0)
    if verbleibend <= 0:
        return SpiellogikResponse(
            success=False,
            message="Keine Fertigkeitssteigerungen mehr verfügbar",
            charakter_daten=daten,
        )

    fert = daten["fertigkeiten"][fert_name]
    wuerfel = fert.get("wuerfel", {"value": 4, "modifier": -2})
    wert = wuerfel.get("value", 4)
    modifier = wuerfel.get("modifier", -2)

    attr_name = fert.get("attribut", "")
    attr_wert = daten.get("attribute", {}).get(attr_name, {}).get("wert", 4)

    # Steigerung ÜBER das verknüpfte Attribut kostet 2 Punkte —
    # maßgeblich ist der neue Wert, also wert >= attr_wert vor der Steigerung
    kosten = 1
    if wert >= attr_wert:
        kosten = 2

    if modifier == -2:
        wuerfel["modifier"] = 0
        kosten = 1
    elif wert == 12 and modifier < 2:
        wuerfel["modifier"] = modifier + 1
    elif wert < 12:
        wuerfel["value"] = wert + 2
    else:
        return SpiellogikResponse(success=False, message="Maximum erreicht", charakter_daten=daten)

    if verbleibend < kosten:
        return SpiellogikResponse(
            success=False,
            message=f"Nicht genug Punkte ({kosten} benötigt, {verbleibend} verfügbar)",
            charakter_daten=daten,
        )

    fert["wuerfel"] = wuerfel
    fert["ausgewaehlt"] = True
    daten["fertigkeiten"][fert_name] = fert
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
    refund = 2 if wert > attr_wert else 1

    if wert == 12 and modifier > 0:
        wuerfel["modifier"] = modifier - 1
    elif wert > 4:
        wuerfel["value"] = wert - 2
    elif wert == 4 and modifier == 0 and not grundfertigkeit:
        wuerfel["modifier"] = -2
        refund = 1
    else:
        return SpiellogikResponse(success=False, message="Minimum erreicht", charakter_daten=daten)

    fert["wuerfel"] = wuerfel
    if wuerfel["value"] == 4 and wuerfel["modifier"] == -2:
        fert["ausgewaehlt"] = False
    daten["fertigkeiten"][fert_name] = fert
    daten["verbleibende_fertigkeitssteigerungen"] = daten.get("verbleibende_fertigkeitssteigerungen", 0) + refund
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/handicap/waehlen", response_model=SpiellogikResponse)
def handicap_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    handicap_name = req.element_name
    setting_name = daten.get("active_setting_name", "SWAE")

    try:
        setting = _load_setting(setting_name)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    handicap_data = setting.get("handicaps", {}).get(handicap_name)
    if not handicap_data:
        return SpiellogikResponse(success=False, message=f"Handicap '{handicap_name}' nicht gefunden")

    selected = daten.get("selected_handicaps", [])
    if handicap_name in selected:
        return SpiellogikResponse(success=False, message=f"'{handicap_name}' bereits ausgewählt")

    stufe = handicap_data.get("stufe", "leicht").lower()
    punkte = 1 if stufe == "leicht" else 2
    gesamt = daten.get("gesamt_handicap_punkte", 0)
    if gesamt + punkte > 4:
        return SpiellogikResponse(success=False, message="Maximale Handicap-Punkte (4) erreicht")

    selected.append(handicap_name)
    daten["selected_handicaps"] = selected
    daten["gesamt_handicap_punkte"] = gesamt + punkte
    daten["verbleibende_handicap_punkte"] = daten.get("verbleibende_handicap_punkte", 0) + punkte
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

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting = _load_setting(setting_name)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    handicap_data = setting.get("handicaps", {}).get(handicap_name, {})
    stufe = handicap_data.get("stufe", "leicht").lower()
    punkte = 1 if stufe == "leicht" else 2

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
    return SpiellogikResponse(success=True, charakter_daten=daten)


HANDICAP_EINLOESE_KOSTEN = {"attribut": 2, "fertigkeit": 1, "talent": 2}


@router.post("/handicap-punkte/einloesen", response_model=SpiellogikResponse)
def handicap_punkte_einloesen(req: SpiellogikRequest):
    daten = req.charakter_daten
    option = req.element_name or ""
    kosten = HANDICAP_EINLOESE_KOSTEN.get(option)
    if kosten is None:
        return SpiellogikResponse(
            success=False,
            message=f"Unbekannte Einlöse-Option '{option}' (gültig: attribut, fertigkeit, talent)",
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
    else:
        feld = "attributsteigerungen" if option == "attribut" else "fertigkeitssteigerungen"
        daten[f"verbleibende_{feld}"] = daten.get(f"verbleibende_{feld}", 0) + 1
        daten[f"maximale_{feld}"] = daten.get(f"maximale_{feld}", 0) + 1
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/talent/waehlen", response_model=SpiellogikResponse)
def talent_waehlen(req: SpiellogikRequest):
    daten = req.charakter_daten
    talent_name = req.element_name
    selected = daten.get("selected_talente", [])

    if talent_name in selected:
        return SpiellogikResponse(success=False, message=f"'{talent_name}' bereits ausgewählt")

    setting_name = daten.get("active_setting_name", "SWAE")
    try:
        setting_talente = _load_setting(setting_name).get("talente", {})
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    talent_data = setting_talente.get(talent_name)
    if not talent_data:
        return SpiellogikResponse(success=False, message=f"Talent '{talent_name}' nicht gefunden")

    # Während der Erschaffung ist der Charakter Anfänger
    rang = talent_data.get("rang", "A")
    if not daten.get("char_gen_completed") and rang != "A":
        return SpiellogikResponse(
            success=False,
            message=f"'{talent_name}' erfordert Rang {RANG_NAMEN.get(rang, rang)} — "
            "bei der Erschaffung sind nur Anfänger-Talente wählbar",
        )

    fehlend = pruefe_voraussetzungen(talent_data, daten, setting_talente)
    if fehlend:
        return SpiellogikResponse(
            success=False,
            message=f"Voraussetzungen nicht erfüllt: {', '.join(fehlend)}",
        )

    verbleibend = daten.get("verbleibende_talente", 0)
    if verbleibend <= 0:
        return SpiellogikResponse(
            success=False,
            message="Kein Talent-Slot verfügbar — Handicap-Punkte einlösen (2 Punkte) "
            "oder ein Volk mit freiem Talent wählen",
            charakter_daten=daten,
        )

    selected.append(talent_name)
    daten["selected_talente"] = selected
    daten["verbleibende_talente"] = verbleibend - 1
    return SpiellogikResponse(success=True, charakter_daten=daten)


@router.post("/talent/entfernen", response_model=SpiellogikResponse)
def talent_entfernen(req: SpiellogikRequest):
    daten = req.charakter_daten
    talent_name = req.element_name
    selected = daten.get("selected_talente", [])

    if talent_name not in selected:
        return SpiellogikResponse(success=False, message=f"'{talent_name}' ist nicht ausgewählt")

    if talent_name in daten.get("volk_effekte", {}).get("talente", []):
        return SpiellogikResponse(
            success=False,
            message=f"'{talent_name}' stammt vom gewählten Volk und kann nicht entfernt werden",
        )

    selected.remove(talent_name)
    daten["selected_talente"] = selected
    daten["verbleibende_talente"] = daten.get("verbleibende_talente", 0) + 1
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
        setting = _load_setting(setting_name)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    macht_data = setting.get("maechte", {}).get(macht_name)
    if not macht_data:
        return SpiellogikResponse(success=False, message=f"Macht '{macht_name}' nicht gefunden")

    rang = macht_data.get("rang", "A")
    if not daten.get("char_gen_completed") and rang != "A":
        return SpiellogikResponse(
            success=False,
            message=f"'{macht_name}' erfordert Rang {RANG_NAMEN.get(rang, rang)} — "
            "bei der Erschaffung sind nur Anfänger-Mächte wählbar",
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

    selected.remove(macht_name)
    daten["selected_maechte"] = selected
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
        setting = _load_setting(setting_name)
    except HTTPException:
        return SpiellogikResponse(success=False, message=f"Setting '{setting_name}' nicht gefunden")

    volk_data = setting.get("voelker", {}).get(volk_name)
    if not volk_data:
        return SpiellogikResponse(success=False, message=f"Volk '{volk_name}' nicht gefunden")

    daten = wende_volk_an(daten, volk_name, volk_data)
    return SpiellogikResponse(success=True, charakter_daten=daten)


_BERECHNE_STATS = ("parade", "robustheit", "bewegungsweite", "groesse", "bennys")


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
        # bedingung "keine_getragene_ruestung": Rüstung wird noch nicht verwaltet,
        # die Bedingung gilt daher immer als erfüllt
        effekt.pop("bedingung", None)
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

    # Volk: Boni stehen strukturiert im effects-Objekt des gewählten Volkes
    for volk_data in daten.get("voelker_selected", {}).values():
        effekte = volk_data.get("effects") or {}
        boni["bewegungsweite"] += effekte.get("bewegungsweite_bonus", 0)
        boni["robustheit"] += effekte.get("robustheit_bonus", 0)
        boni["groesse"] += effekte.get("groesse_modifikator", 0)

    return boni


@router.post("/berechne")
def berechne_abgeleitete_werte(req: SpiellogikRequest):
    daten = req.charakter_daten

    try:
        setting = load_setting(daten.get("active_setting_name", ""))
    except FileNotFoundError:
        setting = {}

    kon_wert = daten.get("attribute", {}).get("Konstitution", {}).get("wert", 4)
    kaempfen = daten.get("fertigkeiten", {}).get("Kämpfen", {})
    kaempfen_wuerfel = kaempfen.get("wuerfel", {"value": 4, "modifier": -2})
    kaempfen_ungelernt = kaempfen_wuerfel.get("modifier", 0) == -2
    kaempfen_wert = 0 if kaempfen_ungelernt else kaempfen_wuerfel.get("value", 4)

    boni = _sammle_effekt_boni(daten, setting)
    macht_slots, machtpunkte = macht_kapazitaet(daten, setting.get("talente", {}))

    groesse = boni["groesse"]
    parade = 2 + (kaempfen_wert // 2) + boni["parade"]
    # Größe fließt nach SWAE in die Robustheit ein
    robustheit = 2 + (kon_wert // 2) + boni["robustheit"] + groesse
    bewegungsweite = 6 + boni["bewegungsweite"]
    bennys = 3 + boni["bennys"]

    return {
        "parade": parade,
        "robustheit": robustheit,
        "bewegungsweite": bewegungsweite,
        "groesse": groesse,
        "bennys": bennys,
        "machtpunkte": machtpunkte,
        "verbleibende_maechte": max(0, macht_slots - len(daten.get("selected_maechte", []))),
        "verbleibende_attributsteigerungen": daten.get("verbleibende_attributsteigerungen", 5),
        "verbleibende_fertigkeitssteigerungen": daten.get("verbleibende_fertigkeitssteigerungen", 12),
        "verbleibende_handicap_punkte": daten.get("verbleibende_handicap_punkte", 0),
        "verbleibende_talente": daten.get("verbleibende_talente", 0),
    }
