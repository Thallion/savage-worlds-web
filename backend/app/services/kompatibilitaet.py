"""Verbotene Talent-Handicap-Kombinationen (Original: kompatibilitaets_pruefung.py)."""


def _handicap_basis(name: str) -> str:
    return name[:-7] if name.endswith(("_leicht", "_schwer")) else name


# (Talente, Handicap-Basisnamen), die sich gegenseitig ausschließen
UNVERTRAEGLICHE_KOMBINATIONEN: list[tuple[set[str], set[str]]] = [
    ({"Reich", "Stinkreich"}, {"Arm"}),
]


def talent_konflikt(talent_name: str, daten: dict) -> str | None:
    """Meldung, wenn das Talent mit einem gewählten Handicap kollidiert."""
    gewaehlt = {_handicap_basis(h) for h in daten.get("selected_handicaps", [])}
    for talente, handicaps in UNVERTRAEGLICHE_KOMBINATIONEN:
        if talent_name in talente and gewaehlt & handicaps:
            konflikt = ", ".join(sorted(gewaehlt & handicaps))
            return f"'{talent_name}' ist nicht mit dem Handicap '{konflikt}' kombinierbar"
    return None


def handicap_konflikt(handicap_name: str, daten: dict) -> str | None:
    """Meldung, wenn das Handicap mit einem gewählten Talent kollidiert."""
    basis = _handicap_basis(handicap_name)
    gewaehlt = set(daten.get("selected_talente", []))
    for talente, handicaps in UNVERTRAEGLICHE_KOMBINATIONEN:
        if basis in handicaps and gewaehlt & talente:
            konflikt = ", ".join(sorted(gewaehlt & talente))
            return f"'{handicap_name}' ist nicht mit dem Talent '{konflikt}' kombinierbar"
    return None
