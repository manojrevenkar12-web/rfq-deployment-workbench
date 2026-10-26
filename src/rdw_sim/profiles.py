"""Three fictional industrial suppliers and what their buyers ask of them.

Each profile holds the supplier's real capabilities (the truth the workbench never sees), the ways buyers write
requirements in German and English (more phrasings than the workbench's vocabulary knows), background sentences
that look like requirements but are not, and how the supplier's quote process behaves.

Companies, buyers and people are invented. Norm numbers are real standards of each industry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Kind:
    """A requirement kind and the supplier's limits for it.

    op: "max"   a requested value v is met when v <= standard; clarify up to limit; deviate beyond.
        "min"   met when v >= standard; clarify down to limit; deviate below.
        "range" a requested (lo, hi) is met inside the standard range; clarify inside the limit range.
        "set"   met when v is in standard; clarify when in limit; deviate otherwise.
        "bool"  met when the supplier has it (standard True); clarify when limit True (on the roadmap).
    """

    name: str
    op: str
    standard: Any
    limit: Any
    severity: str  # if deviating on a mandatory requirement: knockout | major | minor
    commercial: bool = False
    unit: str | None = None


@dataclass(frozen=True)
class Template:
    kind: str
    values: list[Any]  # sampled uniformly; include values beyond the supplier's limits
    de: list[str]  # {v}, {lo}, {hi}, {muss}, {muessen}, {darf}, {ist}
    en: list[str]  # {v}, {lo}, {hi}, {shall}
    norm: str | None = None  # a norm the sentence cites, if any


@dataclass(frozen=True)
class Variant:
    name: str
    subject: str  # what buyers call it (the tender subject)
    subject_en: str
    fits: dict[str, Any] = field(default_factory=dict)  # kind -> limit this variant covers


@dataclass(frozen=True)
class Process:
    tenders_per_year: int
    resources: dict[str, int]  # role -> people
    service_hours: dict[str, tuple[float, float]]  # activity -> (mean hours, coefficient of variation)
    clarification_rate: float  # share of tenders that need a clarification round with the buyer
    buyer_answer_hours: tuple[float, float]  # how long buyers take to answer (calendar hours)
    no_bid_rate: float
    bottleneck: str  # where the process really waits (truth, for checking discovery)


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    domain: str
    languages: dict[str, float]  # share of tenders per language
    kinds: dict[str, Kind]
    templates: list[Template]
    norms_certified: list[str]
    norms_not_certified: list[str]
    variants: list[Variant]
    variant_kind: str  # the kind that picks the variant
    buyers: list[str]
    background_de: list[str]
    background_en: list[str]
    process: Process
    pilot_tenders: int


def _commercial(
    penalty: tuple[float, float],
    warranty: tuple[int, int],
    payment: tuple[int, int],
    delivery_weeks: tuple[int, int],
    spare_years: int,
    training: tuple[int, int],
) -> dict[str, Kind]:
    return {
        "penalty_cap_percent": Kind("penalty_cap_percent", "max", penalty[0], penalty[1], "major", True, "%"),
        "warranty_months": Kind("warranty_months", "max", warranty[0], warranty[1], "major", True, "months"),
        "payment_days": Kind("payment_days", "max", payment[0], payment[1], "minor", True, "days"),
        "liability": Kind("liability", "set", ["contract_value", "limited"], ["double_contract_value"], "major", True),
        "delivery_weeks": Kind("delivery_weeks", "min", delivery_weeks[0], delivery_weeks[1], "major", True, "weeks"),
        "spare_parts_years": Kind("spare_parts_years", "max", spare_years, spare_years, "minor", True, "years"),
        "training_days": Kind("training_days", "max", training[0], training[1], "minor", True, "days"),
        "documentation_language": Kind("documentation_language", "set", ["de", "en"], ["fr"], "minor", True),
        "bid_validity_days": Kind("bid_validity_days", "max", 90, 120, "minor", True, "days"),
    }


COMMERCIAL_TEMPLATES = [
    Template(
        "penalty_cap_percent",
        [3, 5, 5, 8, 10, None],
        [
            "Bei Überschreitung des vereinbarten Liefertermins wird eine Vertragsstrafe von 0,2 % des Auftragswertes je Werktag fällig, insgesamt höchstens {v} % des Auftragswertes.",
            "Für jede angefangene Woche Lieferverzug ist eine Vertragsstrafe von 1 % zu zahlen, begrenzt auf {v} % der Netto-Auftragssumme.",
            "Die Vertragsstrafe bei Terminverzug beträgt 0,3 % je Kalendertag, maximal {v} % des Auftragswerts.",
        ],
        [
            "In case of late delivery, liquidated damages of 0.5 % of the contract value per week shall apply, capped at {v} % of the contract value.",
            "Delay penalties of 0.2 % per working day shall be payable, limited to {v} % of the order value.",
        ],
    ),
    Template(
        "warranty_months",
        [12, 24, 24, 36, 48, 60],
        [
            "Die Gewährleistungsfrist beträgt {v} Monate ab Abnahme.",
            "Der Auftragnehmer übernimmt eine Gewährleistung von {v} Monaten ab der förmlichen Abnahme.",
            "Für alle Lieferungen und Leistungen gilt eine Mängelhaftung von {y} Jahren nach Abnahme.",
        ],
        [
            "The warranty period shall be {v} months from acceptance.",
            "The supplier shall provide a warranty of {y} years after final acceptance.",
        ],
    ),
    Template(
        "payment_days",
        [14, 30, 30, 45, 60, 90],
        [
            "Die Zahlung erfolgt {v} Tage nach Abnahme und Eingang einer prüffähigen Rechnung.",
            "Rechnungen werden innerhalb von {v} Tagen nach Eingang beglichen; Anzahlungen werden nicht geleistet.",
        ],
        ["Payment shall be made {v} days after acceptance and receipt of a correct invoice."],
    ),
    Template(
        "liability",
        ["contract_value", "unlimited", "contract_value", "double_contract_value"],
        [
            "Die Haftung des Auftragnehmers ist {liab_de}.",
            "Der Auftragnehmer haftet für Schäden aus diesem Vertrag {liab_de2}.",
        ],
        ["The supplier's liability under this contract shall be {liab_en}."],
    ),
    Template(
        "delivery_weeks",
        [20, 30, 40, 52, 60, 78],
        [
            "Die Lieferung {muss} spätestens {v} Wochen nach Zuschlagserteilung erfolgen.",
            "Liefertermin: spätestens {m} Monate nach Auftragserteilung.",
            "Die betriebsbereite Übergabe {ist} innerhalb von {v} Wochen nach Vertragsschluss sicherzustellen.",
        ],
        [
            "Delivery {shall} take place no later than {v} weeks after contract award.",
            "The equipment {shall} be handed over ready for operation within {m} months of the order.",
        ],
    ),
    Template(
        "spare_parts_years",
        [5, 10, 10, 15, 20],
        [
            "Ersatzteile {muessen} für mindestens {v} Jahre nach Lieferung verfügbar sein.",
            "Der Auftragnehmer sichert die Ersatzteilversorgung für einen Zeitraum von {v} Jahren zu.",
        ],
        ["Spare parts {shall} remain available for at least {v} years after delivery."],
    ),
    Template(
        "training_days",
        [1, 2, 3, 5, 8],
        [
            "Der Auftragnehmer hat eine Einweisung des Bedienpersonals im Umfang von {v} Tagen durchzuführen.",
            "Die Schulung des Personals {muss} mindestens {v} Schulungstage umfassen.",
        ],
        ["The supplier {shall} provide operator training of {v} days."],
    ),
    Template(
        "documentation_language",
        ["de", "de", "en", "fr"],
        [
            "Die gesamte technische Dokumentation {ist} in {lang_de} Sprache zu liefern.",
            "Betriebsanleitungen und Wartungshandbücher {muessen} in {lang_de} Sprache vorliegen.",
        ],
        ["All technical documentation {shall} be provided in {lang_en}."],
    ),
    Template(
        "bid_validity_days",
        [60, 90, 90, 120, 180],
        [
            "Die Bindefrist für das Angebot beträgt {v} Tage.",
            "Das Angebot {muss} mindestens {v} Kalendertage gültig sein.",
        ],
        ["The offer {shall} remain valid for {v} days."],
    ),
]


GLEISWERK = Profile(
    id="gleiswerk",
    name="Gleiswerk Maschinenbau GmbH",
    domain="rail",
    languages={"de": 0.8, "en": 0.2},
    kinds={
        "travel_speed_kmh": Kind("travel_speed_kmh", "max", 100, 100, "knockout", unit="km/h"),
        "axle_load_t": Kind("axle_load_t", "min", 20.5, 18.0, "knockout", unit="t"),
        "engine_power_kw": Kind("engine_power_kw", "max", 750, 750, "knockout", unit="kW"),
        "emission_stage": Kind("emission_stage", "set", ["V", "IIIB"], ["Tier 4 final"], "major"),
        "ambient_temperature": Kind("ambient_temperature", "range", (-25, 45), (-30, 45), "major", unit="°C"),
        "track_gauge_mm": Kind("track_gauge_mm", "set", [1435, 1000], [], "knockout", unit="mm"),
        "fire_protection_level": Kind("fire_protection_level", "set", ["HL1", "HL2"], [], "knockout"),
        "noise_dba": Kind("noise_dba", "min", 78, 75, "minor", unit="dB(A)"),
        "availability_percent": Kind("availability_percent", "max", 95, 97, "major", unit="%"),
        "gradient_permille": Kind("gradient_permille", "max", 40, 40, "knockout", unit="‰"),
        "norm": Kind("norm", "set", [], [], "major"),
        **_commercial((5, 8), (24, 36), (30, 60), (52, 44), 15, (5, 8)),
    },
    templates=[
        Template(
            "travel_speed_kmh",
            [80, 90, 100, 100, 120],
            [
                "Die Höchstgeschwindigkeit bei Eigenfahrt {muss} mindestens {v} km/h betragen.",
                "Die Maschine {muss} im Überführungsmodus eine Geschwindigkeit von {v} km/h erreichen.",
            ],
            ["The machine {shall} reach a travel speed of at least {v} km/h in self-propelled mode."],
        ),
        Template(
            "axle_load_t",
            [22.5, 22.5, 20.0, 18.0, 16.0],
            ["Die Radsatzlast {darf} {v} t nicht überschreiten.", "Zulässige Radsatzlast: höchstens {vd} t."],
            ["The axle load {shall} not exceed {v} t."],
        ),
        Template(
            "engine_power_kw",
            [400, 560, 560, 750, 900],
            [
                "Die Motorleistung {muss} mindestens {v} kW betragen.",
                "Antriebsleistung des Dieselmotors: mindestens {v} kW.",
            ],
            ["The diesel engine {shall} deliver a rated power of at least {v} kW."],
        ),
        Template(
            "emission_stage",
            ["V", "V", "IIIB", "Tier 4 final"],
            [
                "Der Dieselmotor {muss} die Abgasstufe EU Stufe {v} erfüllen.",
                "Die Abgasemissionen {muessen} den Anforderungen der Stufe {v} entsprechen.",
            ],
            ["The engine {shall} comply with emission stage {v}."],
        ),
        Template(
            "ambient_temperature",
            [(-25, 45), (-20, 40), (-25, 40), (-30, 45), (-40, 40)],
            [
                "Die Maschine {muss} bei Umgebungstemperaturen von {lo} °C bis +{hi} °C uneingeschränkt einsetzbar sein.",
                "Einsatztemperaturbereich: {lo}°C bis {hi}°C.",
            ],
            ["The machine {shall} operate at ambient temperatures from {lo} °C to +{hi} °C."],
        ),
        Template(
            "track_gauge_mm",
            [1435, 1435, 1435, 1000, 1520],
            ["Die Maschine {muss} für die Spurweite {v} mm ausgelegt sein.", "Spurweite: {v} mm."],
            ["The machine {shall} be designed for a track gauge of {v} mm."],
        ),
        Template(
            "fire_protection_level",
            ["HL2", "HL2", "HL1", "HL3"],
            [
                "Der Brandschutz {muss} der Gefährdungsstufe {v} nach EN 45545-2 entsprechen.",
                "Brandschutzanforderungen gemäß EN 45545-2, Gefährdungsstufe {v}.",
            ],
            ["Fire protection {shall} meet hazard level {v} according to EN 45545-2."],
            norm="EN 45545-2",
        ),
        Template(
            "noise_dba",
            [85, 80, 78, 75, 72],
            ["Der Schalldruckpegel am Arbeitsplatz {darf} {v} dB(A) nicht überschreiten."],
            ["The sound pressure level at the operator's position {shall} not exceed {v} dB(A)."],
        ),
        Template(
            "availability_percent",
            [90, 95, 95, 97, 99],
            [
                "Die technische Verfügbarkeit {muss} mindestens {v} % betragen.",
                "Gefordert ist eine Verfügbarkeit von mindestens {vd} %.",
            ],
            ["Technical availability {shall} be at least {v} %."],
        ),
        Template(
            "gradient_permille",
            [25, 35, 40, 40, 60],
            ["Die Maschine {muss} Steigungen bis {v} ‰ befahren können."],
            ["The machine {shall} be able to operate on gradients of up to {v} ‰."],
        ),
    ],
    norms_certified=[
        "EN 14033-1",
        "EN 14033-2",
        "EN 14033-3",
        "EN 15746-1",
        "EN 50155",
        "EN 45545-2",
        "EN 15085-2",
        "DIN EN ISO 9001",
        "EN 13715",
    ],
    norms_not_certified=["EN 15746-2", "EN 50126-1", "TSI NOI"],
    variants=[
        Variant("GW Stopf 08", "Gleisstopfmaschine", "track tamping machine", {"engine_power_kw": 560}),
        Variant("GW Schleif 16", "Schienenschleifzug", "rail grinding train", {"engine_power_kw": 750}),
        Variant("GW ZW 2", "Zweiwegebagger", "road-rail excavator", {"engine_power_kw": 400}),
    ],
    variant_kind="subject",
    buyers=[
        "Netzbetrieb Südwest AG",
        "Gleisbau Rheinebene GmbH",
        "Stadtbahn Lindenau",
        "Regionalnetz Ostalb",
        "Northfield Rail Infrastructure",
        "Bergbahnen Allgäu GmbH",
    ],
    background_de=[
        "Das Streckennetz des Auftraggebers umfasst rund {n} km Gleis.",
        "Die bisher eingesetzte Maschine wurde im Jahr {year} beschafft und hat {n} Betriebsstunden erreicht.",
        "Weitere Hinweise zur Instandhaltung sind der EN 50126-1 zu entnehmen.",
        "Der Auftraggeber plant, die Maschine überwiegend im Nachtbetrieb mit Sperrpausen von {h} Stunden einzusetzen.",
        "Im Jahr {year} wurden insgesamt {n} Weichen instand gesetzt.",
    ],
    background_en=[
        "The client's network comprises about {n} km of track.",
        "Further guidance on maintenance can be found in EN 50126-1.",
        "The current machine was purchased in {year} and has reached {n} operating hours.",
    ],
    process=Process(
        tenders_per_year=120,
        resources={"sales": 2, "sales_engineering": 4, "engineering": 1, "quality": 1, "legal": 2, "management": 1},
        service_hours={
            "Qualify": (2, 0.4),
            "Read requirements": (16, 0.5),
            "Technical review": (12, 0.5),
            "Clarify with buyer": (2, 0.5),
            "Norms check": (4, 0.4),
            "Commercial review": (5, 0.4),
            "Configure and price": (8, 0.4),
            "Write documentation": (14, 0.4),
            "Approve": (1, 0.3),
        },
        clarification_rate=0.35,
        buyer_answer_hours=(72, 0.5),
        no_bid_rate=0.15,
        bottleneck="Technical review",
    ),
    pilot_tenders=36,
)


VOLTARO = Profile(
    id="voltaro",
    name="Voltaro Ladetechnik GmbH",
    domain="charging",
    languages={"de": 0.65, "en": 0.35},
    kinds={
        "charging_power_kw": Kind("charging_power_kw", "max", 400, 400, "knockout", unit="kW"),
        "charge_points": Kind("charge_points", "max", 2, 2, "major"),
        "output_voltage_v": Kind("output_voltage_v", "range", (150, 1000), (150, 1000), "knockout", unit="V"),
        "max_current_a": Kind("max_current_a", "max", 500, 500, "major", unit="A"),
        "efficiency_percent": Kind("efficiency_percent", "max", 95, 96, "minor", unit="%"),
        "ip_rating": Kind("ip_rating", "max", 55, 55, "major"),
        "ambient_temperature": Kind("ambient_temperature", "range", (-30, 50), (-35, 50), "major", unit="°C"),
        "ocpp_version": Kind("ocpp_version", "set", ["1.6J", "2.0.1"], ["2.1"], "major"),
        "iso15118_part": Kind("iso15118_part", "set", ["2"], ["20"], "major"),
        "calibration_law": Kind("calibration_law", "bool", True, True, "knockout"),
        "adhoc_payment": Kind("adhoc_payment", "bool", True, True, "major"),
        "availability_percent": Kind("availability_percent", "max", 97, 98, "major", unit="%"),
        "service_response_hours": Kind("service_response_hours", "min", 24, 8, "major", unit="h"),
        "cable_length_m": Kind("cable_length_m", "max", 5.0, 7.5, "minor", unit="m"),
        "norm": Kind("norm", "set", [], [], "major"),
        **_commercial((5, 10), (24, 60), (30, 60), (16, 12), 10, (2, 3)),
    },
    templates=[
        Template(
            "charging_power_kw",
            [150, 160, 240, 300, 350, 400, 480],
            [
                "Die Ladeleistung je Ladepunkt {muss} mindestens {v} kW betragen.",
                "Jeder Ladepunkt {muss} eine DC-Ladeleistung von {v} kW bereitstellen.",
                "Ladeleistung: {v} kW DC je Ladepunkt (Mindestanforderung).",
            ],
            [
                "Each charge point {shall} deliver at least {v} kW DC.",
                "The charger {shall} provide a charging power of {v} kW per connector.",
            ],
        ),
        Template(
            "charge_points",
            [1, 2, 2, 4],
            ["Jede Ladesäule {muss} über {v} gleichzeitig nutzbare Ladepunkte verfügen."],
            ["Each charging station {shall} provide {v} charge points that can be used simultaneously."],
        ),
        Template(
            "output_voltage_v",
            [(200, 920), (150, 1000), (150, 1000), (50, 1000)],
            ["Der Ausgangsspannungsbereich {muss} {lo} V bis {hi} V abdecken.", "Ausgangsspannung: {lo}–{hi} V DC."],
            ["The output voltage range {shall} cover {lo} V to {hi} V."],
        ),
        Template(
            "max_current_a",
            [300, 400, 500, 600],
            ["Der maximale Ladestrom {muss} mindestens {v} A betragen."],
            ["The maximum charging current {shall} be at least {v} A."],
        ),
        Template(
            "efficiency_percent",
            [94, 95, 95, 96, 97],
            ["Der Wirkungsgrad bei Nennleistung {muss} mindestens {vd} % betragen."],
            ["Efficiency at rated power {shall} be at least {v} %."],
        ),
        Template(
            "ip_rating",
            [54, 55, 55, 65],
            [
                "Die Ladesäule {muss} mindestens die Schutzart IP{v} nach IEC 60529 aufweisen.",
                "Schutzart des Gehäuses: IP{v}.",
            ],
            ["The enclosure {shall} have a protection rating of at least IP{v} according to IEC 60529."],
            norm="IEC 60529",
        ),
        Template(
            "ambient_temperature",
            [(-25, 45), (-30, 50), (-30, 50), (-35, 50), (-40, 55)],
            [
                "Die Ladeinfrastruktur {muss} bei Umgebungstemperaturen von {lo} °C bis +{hi} °C betrieben werden können."
            ],
            ["The charger {shall} operate at ambient temperatures from {lo} °C to +{hi} °C."],
        ),
        Template(
            "ocpp_version",
            ["1.6J", "2.0.1", "2.0.1", "2.1"],
            [
                "Die Anbindung an das Backend {muss} über OCPP {v} erfolgen.",
                "Kommunikationsprotokoll zum Backend: OCPP {v}.",
            ],
            ["The charger {shall} connect to the backend via OCPP {v}."],
        ),
        Template(
            "iso15118_part",
            ["2", "2", "20"],
            ["Plug & Charge {muss} nach ISO 15118-{v} unterstützt werden."],
            ["Plug & Charge {shall} be supported according to ISO 15118-{v}."],
            norm="ISO 15118-{v}",
        ),
        Template(
            "calibration_law",
            [True],
            [
                "Die Ladesäulen {muessen} eichrechtskonform nach PTB-A 50.7 sein.",
                "Die Abrechnung {muss} den Anforderungen des Mess- und Eichrechts entsprechen.",
            ],
            ["The chargers {shall} comply with German calibration law (Eichrecht, PTB-A 50.7)."],
            norm="PTB-A 50.7",
        ),
        Template(
            "adhoc_payment",
            [True],
            [
                "Ein Ad-hoc-Laden mit Debit- und Kreditkarte {muss} gemäß AFIR am Ladepunkt möglich sein.",
                "Für das punktuelle Laden {ist} ein Kartenterminal für gängige Zahlungskarten vorzusehen.",
            ],
            ["Ad-hoc charging by debit and credit card {shall} be possible at the charge point as required by AFIR."],
        ),
        Template(
            "availability_percent",
            [95, 97, 97, 98, 99],
            ["Die Verfügbarkeit der Ladepunkte {muss} im Jahresmittel mindestens {vd} % betragen."],
            ["Annual availability of the charge points {shall} be at least {v} %."],
        ),
        Template(
            "service_response_hours",
            [48, 24, 24, 8, 4],
            [
                "Der Servicetechniker {muss} innerhalb von {v} Stunden nach Störungsmeldung vor Ort sein.",
                "Reaktionszeit im Störungsfall: maximal {v} h.",
            ],
            ["A service technician {shall} be on site within {v} hours of a fault report."],
        ),
        Template(
            "cable_length_m",
            [4.0, 5.0, 5.0, 7.5, 10.0],
            ["Die Länge der Ladekabel {muss} mindestens {vd} m betragen."],
            ["The charging cables {shall} be at least {v} m long."],
        ),
    ],
    norms_certified=[
        "IEC 61851-1",
        "IEC 61851-23",
        "IEC 62196-3",
        "ISO 15118-2",
        "EN 61000-6-2",
        "EN 61000-6-4",
        "IEC 60529",
        "IEC 62262",
        "VDE-AR-N 4100",
        "PTB-A 50.7",
    ],
    norms_not_certified=["ISO 15118-20", "VDE-AR-N 4110"],
    variants=[
        Variant("VOLT 160", "Schnellladesäule", "fast charger", {"charging_power_kw": 160}),
        Variant("VOLT 240", "Schnellladesäule", "fast charger", {"charging_power_kw": 240}),
        Variant("VOLT 400", "Schnellladesäule", "fast charger", {"charging_power_kw": 400}),
    ],
    variant_kind="charging_power_kw",
    buyers=[
        "Stadtwerke Lindenau",
        "Energieversorgung Mittelrhein",
        "Kommunalbetriebe Waldbach",
        "Fleetway Logistics BV",
        "Autobahnservice Nord GmbH",
        "Nordic Charge Partners AB",
    ],
    background_de=[
        "Die Stadtwerke betreiben derzeit {n} öffentliche Ladepunkte im Stadtgebiet.",
        "Am Standort steht ein Netzanschluss mit {n} kVA zur Verfügung.",
        "Informationen zum Netzanschluss in der Mittelspannung enthält die VDE-AR-N 4110.",
        "Im Jahr {year} wurden an den bestehenden Ladepunkten rund {n} MWh abgegeben.",
    ],
    background_en=[
        "The operator currently runs {n} public charge points.",
        "A grid connection of {n} kVA is available at the site.",
        "In {year}, the existing charge points delivered about {n} MWh.",
    ],
    process=Process(
        tenders_per_year=300,
        resources={"sales": 3, "sales_engineering": 4, "engineering": 2, "quality": 1, "legal": 1, "management": 1},
        service_hours={
            "Qualify": (1, 0.4),
            "Read requirements": (6, 0.5),
            "Technical review": (4, 0.5),
            "Clarify with buyer": (1.5, 0.5),
            "Norms check": (2, 0.4),
            "Commercial review": (6.5, 0.5),
            "Configure and price": (3, 0.4),
            "Write documentation": (6, 0.4),
            "Approve": (0.5, 0.3),
        },
        clarification_rate=0.25,
        buyer_answer_hours=(48, 0.5),
        no_bid_rate=0.2,
        bottleneck="Commercial review",
    ),
    pilot_tenders=40,
)


BRANDT = Profile(
    id="brandt",
    name="Brandt Fahrzeugbau GmbH",
    domain="fire",
    languages={"de": 1.0},
    kinds={
        "vehicle_type": Kind("vehicle_type", "set", ["HLF 10", "HLF 20", "TLF 3000"], ["LF 20"], "knockout"),
        "gross_mass_t": Kind("gross_mass_t", "max", 16, 18, "knockout", unit="t"),
        "water_tank_l": Kind("water_tank_l", "max", 3000, 5000, "major", unit="l"),
        "foam_tank_l": Kind("foam_tank_l", "max", 500, 800, "minor", unit="l"),
        "fire_pump": Kind("fire_pump", "set", ["FPN 10-2000", "FPN 10-3000"], ["FPN 10-4000"], "knockout"),
        "crew_cab": Kind("crew_cab", "set", ["1+8", "1+5", "1+2"], [], "major"),
        "generator_kva": Kind("generator_kva", "max", 14, 20, "minor", unit="kVA"),
        "light_mast": Kind("light_mast", "bool", True, True, "minor"),
        "drive": Kind("drive", "set", ["4x2", "4x4"], ["6x6"], "knockout"),
        "norm": Kind("norm", "set", [], [], "major"),
        **_commercial((5, 5), (24, 36), (30, 30), (78, 70), 15, (3, 5)),
    },
    templates=[
        Template(
            "vehicle_type",
            ["HLF 20", "HLF 20", "HLF 10", "TLF 3000", "LF 20", "DLK 23-12"],
            ["Zu liefern ist ein Fahrzeug vom Typ {v} nach DIN 14530.", "Fahrzeugtyp: {v}."],
            [],
            norm="DIN 14530",
        ),
        Template(
            "gross_mass_t",
            [14, 15, 16, 18, 26],
            [
                "Die zulässige Gesamtmasse des Fahrgestells {darf} {v} t nicht überschreiten.",
                "Fahrgestell mit einer zulässigen Gesamtmasse von höchstens {vd} t.",
            ],
            [],
        ),
        Template(
            "water_tank_l",
            [1000, 2000, 2500, 3000, 4500, 6000],
            [
                "Der Löschwasserbehälter {muss} ein Nennvolumen von mindestens {v} l aufweisen.",
                "Löschwassertank: mindestens {vt} Liter.",
            ],
            [],
        ),
        Template(
            "foam_tank_l",
            [120, 200, 500, 1000],
            ["Es {ist} ein Schaummitteltank mit einem Volumen von {v} l vorzusehen."],
            [],
        ),
        Template(
            "fire_pump",
            ["FPN 10-2000", "FPN 10-2000", "FPN 10-3000", "FPN 10-4000", "FPH 40-250"],
            [
                "Die Feuerlöschkreiselpumpe {muss} der Bauart {v} nach DIN EN 1028-1 entsprechen.",
                "Feuerlöschpumpe: {v} gemäß DIN EN 1028-1.",
            ],
            [],
            norm="DIN EN 1028-1",
        ),
        Template(
            "crew_cab",
            ["1+8", "1+8", "1+5", "1+2", "1+9"],
            ["Die Mannschaftskabine {muss} Sitzplätze für eine Besatzung von {v} bieten.", "Besatzung: {v}."],
            [],
        ),
        Template(
            "generator_kva",
            [8, 13, 14, 20, 30],
            ["Es {ist} ein tragbarer Stromerzeuger mit mindestens {v} kVA vorzusehen."],
            [],
        ),
        Template(
            "light_mast",
            [True],
            ["Das Fahrzeug {muss} mit einem pneumatischen Lichtmast mit LED-Scheinwerfern ausgestattet sein."],
            [],
        ),
        Template(
            "drive",
            ["4x2", "4x4", "4x4", "6x6"],
            ["Der Antrieb des Fahrgestells {muss} als {v} ausgeführt sein.", "Antriebsart: {v}."],
            [],
        ),
    ],
    norms_certified=[
        "DIN EN 1846-1",
        "DIN EN 1846-2",
        "DIN EN 1846-3",
        "DIN 14530-11",
        "DIN 14530-27",
        "DIN EN 1028-1",
        "DIN 14502-2",
        "DIN 14530",
    ],
    norms_not_certified=["DIN EN 14043", "DIN 14502-3"],
    variants=[
        Variant("Brandt HLF 10", "HLF 10", "HLF 10"),
        Variant("Brandt HLF 20", "HLF 20", "HLF 20"),
        Variant("Brandt TLF 3000", "TLF 3000", "TLF 3000"),
    ],
    variant_kind="vehicle_type",
    buyers=[
        "Gemeinde Waldbach",
        "Stadt Lindenau",
        "Markt Oberhausen am See",
        "Verbandsgemeinde Hunsrückhöhe",
        "Stadt Neuweiler",
        "Gemeinde Talheim",
    ],
    background_de=[
        "Die Freiwillige Feuerwehr verfügt derzeit über ein LF 16/12 aus dem Jahr {year}.",
        "Das Gerätehaus bietet eine Stellplatzhöhe von {m} m.",
        "Hinweise zu Drehleitern enthält die DIN EN 14043.",
        "Im Jahr {year} rückte die Wehr zu {n} Einsätzen aus.",
        "Die Beladung wird teilweise aus dem bisherigen Fahrzeug übernommen.",
    ],
    background_en=[],
    process=Process(
        tenders_per_year=90,
        resources={"sales": 2, "sales_engineering": 3, "engineering": 2, "quality": 1, "legal": 1, "management": 1},
        service_hours={
            "Qualify": (1.5, 0.4),
            "Read requirements": (12, 0.5),
            "Technical review": (6, 0.5),
            "Clarify with buyer": (3, 0.5),
            "Norms check": (3, 0.4),
            "Commercial review": (3, 0.4),
            "Configure and price": (10, 0.4),
            "Write documentation": (10, 0.4),
            "Approve": (1, 0.3),
        },
        clarification_rate=0.6,
        buyer_answer_hours=(240, 0.6),
        no_bid_rate=0.1,
        bottleneck="Buyer answer",
    ),
    pilot_tenders=32,
)

PROFILES: dict[str, Profile] = {p.id: p for p in (GLEISWERK, VOLTARO, BRANDT)}
