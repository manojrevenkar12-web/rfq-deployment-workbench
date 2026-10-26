# Writing a held-out tender set

You are writing tenders that the workbench has never seen, and the answer key a careful sales engineer at the
supplier would produce for each. The set measures how well the agents work on text written by someone else.

**Rules for the writer**

- Read only this file. Do not open the code, the configuration (`config/`), the simulator (`src/rdw_sim`) or
  any generated data (`data/`). If you have seen them, say so and do not write a set.
- Write the way buyers really write: vary sentence structure, mix modal verbs, put numbers in different forms
  (`22,5 t`, `4.500 Liter`, `0,3 MW`, `zwei Jahre`, `18 Monate`), split requirements across sentences, add
  background text with numbers that is *not* a requirement, cite norms both as requirements and in passing.
- Do not try to trick a parser with nonsense. Write what a real public or industrial buyer would send.

## What to write

For each customer below, write **8 tenders** in `heldout/<set>/<customer>/<tender-id>/spec.md` and the key in
`heldout/<set>/<customer>/<tender-id>.answer.json`. Tender ids: `HO-<customer>-01` … `HO-<customer>-08`.

`spec.md` format:

```
# Leistungsbeschreibung: <subject, e.g. Beschaffung einer Gleisstopfmaschine>
Auftraggeber: <invented buyer>

1 Allgemeines
1.1 <background sentence>
...
2 Technische Anforderungen
2.1 <requirement sentence>
...
3 <more sections as you like: Normen, Vertragsbedingungen, Angebotsabgabe>
```

- English tenders use `# Technical specification: <subject>` and `Contracting authority: <buyer>`.
- Numbered items (`2.1`, `2.2`, …) of one or more sentences. Headings are `<number> <title>` without a full stop.
- No tables. One requirement per sentence; a numbered item may hold several sentences.
- Each tender: 10–20 product requirements, 4–8 contract terms, 2–4 norms required in their own sentence,
  2–4 obligations about the bid itself (submission, references, insurance), 2–5 background sentences.
- About a quarter of the requirements desirable rather than mandatory (`soll`, `sollte`, `wünschenswert`,
  `should`, `desirable`).
- Include requirements the supplier cannot meet or must clarify (see the facts), so that some tenders end in
  no bid.

## The answer key

```json
{
  "id": "HO-voltaro-01",
  "customer": "voltaro",
  "language": "de",
  "subject": "...",
  "requirements": [
    {"text": "<the sentence exactly as in spec.md, without its item number>",
     "doc": "spec", "kind": "charging_power_kw", "value": 300, "unit": "kW",
     "priority": "mandatory", "verdict": "comply", "severity": null, "red_flag": false,
     "norms": []}
  ],
  "norms": {"IEC 61851-23": "certified"},
  "bid": "bid",
  "variant": "VOLT 400"
}
```

- `text`: one sentence. If an item has two sentences with two requirements, write two entries.
- Background sentences and sentences that only mention a norm in passing are **not** requirements.
- `kind`: from the lists below. Obligations about the bid itself: `procedural` (value null, verdict comply).
  A sentence whose only content is that a norm must be met: kind `norm`, value the norm (e.g. `"EN 50155"`).
- `value`: numbers as numbers in the unit of the kind (warranty in months: "zwei Jahre" is 24; delivery in
  weeks: months × 52 / 12, rounded to one decimal; power in kW). Ranges as `[low, high]`. Enumerations as the
  short code shown below. `true` for features that are simply required. An uncapped penalty is `null`.
- `priority`: `mandatory` or `desirable`.
- `verdict`, by the supplier's facts: a value within *standard* is `comply`; beyond standard but within
  *limit* is `clarify`; beyond the limit is `deviate`. For lists: in standard `comply`, in limit `clarify`,
  otherwise `deviate`. Norms: certified `comply`, not certified `deviate`. Procedural: `comply`.
- `red_flag`: true when the verdict is `deviate`, or when it is `clarify` on a contract term of severity major.
- `severity` (only when `red_flag`): desirable requirements `minor`; a mandatory `deviate` takes the kind's
  severity below (norms: `major`); a mandatory `clarify` is `major` if the kind's severity is knockout or
  major, else `minor`.
- `norms`: norms the sentence cites. The top-level `norms` lists every norm cited by a requirement with
  `certified` or `not_certified` (from the facts).
- `bid`: `no_bid` when any mandatory requirement is `deviate` with severity knockout, or when no product
  variant fits; otherwise `bid`.
- `variant`: the product variant (rules per customer below), or `null` when none fits.

## Contract terms (all customers)

| kind | value | meaning |
| --- | --- | --- |
| `penalty_cap_percent` | % | the cap on delay penalties (null = no cap: always deviate) |
| `warranty_months` | months | warranty period asked for |
| `payment_days` | days | payment term |
| `liability` | `contract_value`, `limited` (a fixed amount), `double_contract_value`, `unlimited` | liability cap |
| `delivery_weeks` | weeks | latest delivery after award |
| `spare_parts_years` | years | spare parts availability asked for |
| `training_days` | days | training asked for |
| `documentation_language` | `de`, `en`, `fr` | documentation language |
| `bid_validity_days` | days | how long the offer must stay valid |

## Gleiswerk Maschinenbau GmbH (rail maintenance machines)

Product variants (chosen by what the tender buys): tamping machine (Gleisstopfmaschine) → `GW Stopf 08`;
rail grinding train (Schienenschleifzug) → `GW Schleif 16`; road-rail excavator (Zweiwegebagger) → `GW ZW 2`.

| kind | standard | limit | severity |
| --- | --- | --- | --- |
| `travel_speed_kmh` (minimum speed asked) | ≤ 100 | ≤ 100 | knockout |
| `axle_load_t` (maximum axle load allowed by the buyer) | ≥ 20.5 | ≥ 18.0 | knockout |
| `engine_power_kw` (minimum power asked) | ≤ 750 | ≤ 750 | knockout |
| `emission_stage` (`V`, `IIIB`, `Tier 4 final`) | V, IIIB | Tier 4 final | major |
| `ambient_temperature` °C range asked | within −25…45 | within −30…45 | major |
| `track_gauge_mm` | 1435, 1000 | none | knockout |
| `fire_protection_level` (EN 45545-2 `HL1`…`HL3`) | HL1, HL2 | none | knockout |
| `noise_dba` (maximum allowed by the buyer) | ≥ 78 | ≥ 75 | minor |
| `availability_percent` (minimum asked) | ≤ 95 | ≤ 97 | major |
| `gradient_permille` | ≤ 40 | ≤ 40 | knockout |
| penalty cap % | ≤ 5 | ≤ 8 | major |
| warranty months | ≤ 24 | ≤ 36 | major |
| payment days | ≤ 30 | ≤ 60 | minor |
| liability | contract_value, limited | double_contract_value | major |
| delivery weeks (≥) | ≥ 52 | ≥ 44 | major |
| spare parts years | ≤ 15 | ≤ 15 | minor |
| training days | ≤ 5 | ≤ 8 | minor |
| documentation language | de, en | fr | minor |
| bid validity days | ≤ 90 | ≤ 120 | minor |

Certified: EN 14033-1, EN 14033-2, EN 14033-3, EN 15746-1, EN 50155, EN 45545-2, EN 15085-2, DIN EN ISO 9001,
EN 13715. Not certified: EN 15746-2, EN 50126-1, TSI NOI.

## Voltaro Ladetechnik GmbH (DC fast chargers)

Variant: the smallest of `VOLT 160` (160 kW), `VOLT 240`, `VOLT 400` covering the highest charging power per
charge point asked; none above 400 kW.

| kind | standard | limit | severity |
| --- | --- | --- | --- |
| `charging_power_kw` per charge point | ≤ 400 | ≤ 400 | knockout |
| `charge_points` per station | ≤ 2 | ≤ 2 | major |
| `output_voltage_v` range | within 150…1000 | within 150…1000 | knockout |
| `max_current_a` | ≤ 500 | ≤ 500 | major |
| `efficiency_percent` (minimum asked) | ≤ 95 | ≤ 96 | minor |
| `ip_rating` (the number: IP54 → 54) | ≤ 55 | ≤ 55 | major |
| `ambient_temperature` °C | within −30…50 | within −35…50 | major |
| `ocpp_version` (`1.6J`, `2.0.1`, `2.1`) | 1.6J, 2.0.1 | 2.1 | major |
| `iso15118_part` (`2` or `20`, Plug & Charge) | 2 | 20 | major |
| `calibration_law` (German Eichrecht) | true | | knockout |
| `adhoc_payment` (card payment, AFIR) | true | | major |
| `availability_percent` | ≤ 97 | ≤ 98 | major |
| `service_response_hours` (maximum allowed by the buyer) | ≥ 24 | ≥ 8 | major |
| `cable_length_m` | ≤ 5 | ≤ 7.5 | minor |
| penalty cap % | ≤ 5 | ≤ 10 | major |
| warranty months | ≤ 24 | ≤ 60 | major |
| payment days | ≤ 30 | ≤ 60 | minor |
| liability | contract_value, limited | double_contract_value | major |
| delivery weeks (≥) | ≥ 16 | ≥ 12 | major |
| spare parts years | ≤ 10 | ≤ 10 | minor |
| training days | ≤ 2 | ≤ 3 | minor |
| documentation language | de, en | fr | minor |
| bid validity days | ≤ 90 | ≤ 120 | minor |

Certified: IEC 61851-1, IEC 61851-23, IEC 62196-3, ISO 15118-2, EN 61000-6-2, EN 61000-6-4, IEC 60529,
IEC 62262, VDE-AR-N 4100, PTB-A 50.7. Not certified: ISO 15118-20, VDE-AR-N 4110.

## Brandt Fahrzeugbau GmbH (fire-fighting vehicles, German tenders only)

Variant by vehicle type: `HLF 10` → `Brandt HLF 10`, `HLF 20` → `Brandt HLF 20`, `TLF 3000` → `Brandt TLF 3000`;
anything else has no variant.

| kind | standard | limit | severity |
| --- | --- | --- | --- |
| `vehicle_type` (`HLF 10`, `HLF 20`, `TLF 3000`, `LF 20`, `DLK 23-12`, …) | HLF 10, HLF 20, TLF 3000 | LF 20 | knockout |
| `gross_mass_t` | ≤ 16 | ≤ 18 | knockout |
| `water_tank_l` | ≤ 3000 | ≤ 5000 | major |
| `foam_tank_l` | ≤ 500 | ≤ 800 | minor |
| `fire_pump` (`FPN 10-2000`, `FPN 10-3000`, `FPN 10-4000`, `FPH 40-250`) | FPN 10-2000, FPN 10-3000 | FPN 10-4000 | knockout |
| `crew_cab` (`1+8`, `1+5`, `1+2`, …) | 1+8, 1+5, 1+2 | none | major |
| `generator_kva` | ≤ 14 | ≤ 20 | minor |
| `light_mast` | true | | minor |
| `drive` (`4x2`, `4x4`, `6x6`) | 4x2, 4x4 | 6x6 | knockout |
| penalty cap % | ≤ 5 | ≤ 5 | major |
| warranty months | ≤ 24 | ≤ 36 | major |
| payment days | ≤ 30 | ≤ 30 | minor |
| liability | contract_value, limited | double_contract_value | major |
| delivery weeks (≥) | ≥ 78 | ≥ 70 | major |
| spare parts years | ≤ 15 | ≤ 15 | minor |
| training days | ≤ 3 | ≤ 5 | minor |
| documentation language | de, en | fr | minor |
| bid validity days | ≤ 90 | ≤ 120 | minor |

Certified: DIN EN 1846-1, DIN EN 1846-2, DIN EN 1846-3, DIN 14530-11, DIN 14530-27, DIN EN 1028-1,
DIN 14502-2, DIN 14530. Not certified: DIN EN 14043, DIN 14502-3.

## When you are done

Write `heldout/<set>/README.md`: who wrote the set, when, and a statement that the writer did not read the
code, configuration or data. Then stop. Nobody changes the agents to pass this set; its first run is recorded
in `reports/heldout/<set>/first_run.json` and never rewritten.
