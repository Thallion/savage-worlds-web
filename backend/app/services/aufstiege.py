"""Aufstiege und Rang nach der Erschaffung (Original: character_advancement.py).

Nach Abschluss der Erschaffung (char_gen_completed) werden Steigerungen aus
verbleibende_aufstiege bezahlt: Attribut = 1 Aufstieg, Fertigkeit = 0.5
(über dem Attribut das Doppelte), Talent = 1. Der Rang ergibt sich aus den
ausgegebenen Aufstiegen (aufstiege_gesamt - verbleibende_aufstiege).
"""

RANG_MAPPING = [
    (0, 4, "Anfänger"),
    (4, 8, "Fortgeschritten"),
    (8, 12, "Veteran"),
    (12, 16, "Heroisch"),
    (16, 10**9, "Legendär"),
]

# Reihenfolge der Rang-Kürzel aus den Setting-JSONs (talent["rang"])
RANG_REIHENFOLGE = ["A", "F", "V", "H", "L"]

AUFSTIEG_KOSTEN_ATTRIBUT = 1
AUFSTIEG_KOSTEN_FERTIGKEIT = 0.5
AUFSTIEG_KOSTEN_TALENT = 1
# Ein schweres Handicap auf leicht reduzieren oder ein leichtes ganz abkaufen
# kostet je einen Aufstieg (SWADE: "Ein Handicap abkaufen").
AUFSTIEG_KOSTEN_HANDICAP = 1


def ausgegebene_aufstiege(daten: dict) -> float:
    return max(0, daten.get("aufstiege_gesamt", 0) - daten.get("verbleibende_aufstiege", 0))


def charakter_rang(daten: dict) -> str:
    """Voller Rang-Name; während der Erschaffung immer Anfänger."""
    if not daten.get("char_gen_completed"):
        return "Anfänger"
    ausgegeben = ausgegebene_aufstiege(daten)
    for min_val, max_val, name in RANG_MAPPING:
        if min_val <= ausgegeben < max_val:
            return name
    return "Anfänger"


def rang_erlaubt(element_rang: str, daten: dict) -> bool:
    """True, wenn der Rang des Talents/der Macht den Charakterrang nicht übersteigt."""
    rang_name = charakter_rang(daten)
    char_index = next(
        (i for i, (_, _, name) in enumerate(RANG_MAPPING) if name == rang_name), 0
    )
    element_index = (
        RANG_REIHENFOLGE.index(element_rang) if element_rang in RANG_REIHENFOLGE else 0
    )
    return element_index <= char_index
