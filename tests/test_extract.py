from __future__ import annotations

import pytest

from rdw.config import domain_kinds
from rdw.extract import extract, norms_in, parse_number, value_of
from rdw.ingest import Segment, sentences

RAIL = domain_kinds("rail")
CHARGING = domain_kinds("charging")
FIRE = domain_kinds("fire")


def seg(text: str, doc: str = "spec", **meta: str) -> Segment:
    return Segment(doc, "spec.pdf", "page 1", text, meta=dict(meta))


@pytest.mark.parametrize(
    ("raw", "lang", "expected"),
    [
        ("22,5", "de", 22.5),
        ("4.500", "de", 4500),
        ("1,000", "en", 1000),
        ("0.5", "en", 0.5),
        ("−25", "de", -25),
    ],
)
def test_numbers_are_read_the_way_each_language_writes_them(raw: str, lang: str, expected: float) -> None:
    assert parse_number(raw, lang) == expected


def test_values_come_in_the_kinds_unit() -> None:
    assert value_of(CHARGING["charging_power_kw"], "Jede Säule muss 0,3 MW je Ladepunkt leisten.", "de") == 300
    assert value_of(CHARGING["warranty_months"], "Mängelhaftung von 2 Jahren nach Abnahme.", "de") == 24
    assert (
        value_of(CHARGING["delivery_weeks"], "Liefertermin: spätestens 18 Monate nach Auftragserteilung.", "de") == 78.0
    )
    assert value_of(RAIL["ambient_temperature"], "Einsatz bei −30 °C bis +45 °C.", "de") == [-30, 45]
    assert value_of(CHARGING["output_voltage_v"], "Ausgangsspannung: 150–1000 V DC.", "de") == [150, 1000]
    assert value_of(FIRE["water_tank_l"], "Löschwassertank: mindestens 4.500 Liter.", "de") == 4500
    assert (
        value_of(
            CHARGING["charge_points"], "Jede Ladesäule muss über 2 gleichzeitig nutzbare Ladepunkte verfügen.", "de"
        )
        == 2
    )


def test_commercial_terms_are_parsed_including_the_dangerous_ones() -> None:
    k = CHARGING
    assert (
        value_of(k["penalty_cap_percent"], "0,2 % je Werktag, insgesamt höchstens 8 % des Auftragswertes.", "de") == 8
    )
    assert (
        value_of(k["penalty_cap_percent"], "Die Vertragsstrafe ist der Höhe nach nicht begrenzt.", "de") == "unlimited"
    )
    assert value_of(k["liability"], "Die Haftung des Auftragnehmers ist der Höhe nach unbegrenzt.", "de") == "unlimited"
    assert (
        value_of(k["liability"], "The supplier's liability shall be limited to twice the contract value.", "en")
        == "double_contract_value"
    )
    assert value_of(k["documentation_language"], "Handbücher müssen in französischer Sprache vorliegen.", "de") == "fr"


def test_enumerations_are_normalised() -> None:
    assert value_of(FIRE["fire_pump"], "Feuerlöschpumpe: FPN10-3000 gemäß DIN EN 1028-1.", "de") == "FPN 10-3000"
    assert value_of(FIRE["crew_cab"], "Besatzung: 1 + 8.", "de") == "1+8"
    assert value_of(RAIL["fire_protection_level"], "Gefährdungsstufe HL 3 nach EN 45545-2.", "de") == "HL3"
    assert value_of(CHARGING["ip_rating"], "Schutzart des Gehäuses: IP65.", "de") == 65


def test_norms_are_found_and_numbers_in_text_are_not_norms() -> None:
    assert norms_in("Konformität mit DIN EN ISO 9001:2015 und EN 45545-2 ist nachzuweisen.") == [
        "DIN EN ISO 9001",
        "EN 45545-2",
    ]
    assert norms_in("Nachweis nach TSI NOI.") == ["TSI NOI"]


def test_sentences_survive_abbreviations() -> None:
    assert sentences("Die Leistung beträgt mind. 300 kW. Die Schutzart ist z. B. IP55.") == [
        "Die Leistung beträgt mind. 300 kW.",
        "Die Schutzart ist z. B. IP55.",
    ]


def test_background_and_passing_mentions_are_not_requirements() -> None:
    found = extract(
        [
            seg("Die Stadtwerke betreiben derzeit 42 öffentliche Ladepunkte im Stadtgebiet."),
            seg("Informationen zum Netzanschluss enthält die VDE-AR-N 4110."),
            seg("Die Ladeleistung je Ladepunkt muss mindestens 300 kW betragen."),
        ],
        CHARGING,
        "de",
    )
    assert [(f.kind, f.value) for f in found] == [("charging_power_kw", 300)]


def test_priority_from_wording_and_from_the_bill_of_quantities() -> None:
    found = extract(
        [
            seg("Der Wirkungsgrad bei Nennleistung soll mindestens 95 % betragen."),
            seg("Ladeleistung je Ladepunkt: mind. 240 kW", doc="lv", category="Muss"),
            seg("Länge Ladekabel: mind. 7,5 m", doc="lv", category="Soll"),
        ],
        CHARGING,
        "de",
    )
    assert [f.priority for f in found] == ["desirable", "mandatory", "desirable"]


def test_bid_procedure_and_unknown_obligations_are_kept_apart() -> None:
    found = extract(
        [
            seg("Der Bieter hat mit dem Angebot drei Referenzen über vergleichbare Lieferungen vorzulegen."),
            seg("Die Maschine muss rosa lackiert sein."),
        ],
        RAIL,
        "de",
    )
    assert [f.kind for f in found] == ["procedural", "other"]


def test_a_norm_statement_is_a_norm_requirement() -> None:
    found = extract(
        [seg("Nachweis der Erfüllung von EN 15085-2: Zertifikat einer anerkannten Prüfstelle.")], RAIL, "de"
    )
    assert (found[0].kind, found[0].value) == ("norm", "EN 15085-2")
