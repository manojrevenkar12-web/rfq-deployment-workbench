# Held-out tender set v1

Written on 26 October 2026 by a Claude agent (Claude Code), working as an independent writer for
Manoj Kumar P.

The writer read only `heldout/WRITING_TENDERS.md`. The writer did not open, list or search the
code (`src/`), the configuration (`config/`), the simulator, generated data (`data/`), the tests,
or any other held-out set, and did not run the project.

## Contents

- 24 tenders: 8 each for `gleiswerk`, `voltaro` and `brandt`, in `<customer>/HO-<customer>-NN/spec.md`.
- One answer key per tender in `<customer>/HO-<customer>-NN.answer.json`.
- Languages: Gleiswerk 5 German and 3 English (02, 05, 07); Voltaro 6 German and 2 English (02, 05, 08);
  Brandt 8 German.
- 8 tenders end in `no_bid`: gleiswerk 03, 05 and 06; voltaro 04 and 08; brandt 04, 05 and 06
  (brandt 05 has no knockout deviation; it is a no-bid only because no product variant fits).

## Conventions the guide leaves open

These are the writer's own choices, recorded so whoever scores the set knows them:

- Units: `mm`, `t`, `km/h`, `kW`, `°C`, `‰`, `dB(A)`, `%`, `V`, `A`, `h`, `m`, `l`, `kVA`, `weeks`, `months`,
  `days`, `years`. Enumerations, booleans, counts (`charge_points`, `ip_rating`), norms and procedural
  items have `unit: null`.
- `iso15118_part` is written as the string `"2"` or `"20"`, like the other enumeration codes.
- A sentence that names an ISO 15118 part as a feature (Plug & Charge) is kind `iso15118_part`, and its
  verdict comes from that kind's row; the cited norm still appears in `norms` with its certification status.
- `red_flag` for `clarify` applies only to contract terms whose kind severity is major. A `clarify` on a
  product requirement has `red_flag: false` and `severity: null`. No desirable contract term ends in
  `clarify`, so that case does not come up.
- "Normalspur" without a number is keyed as 1435 mm.
- Sentences that say something is *not* needed (for example no card terminal at a closed depot, no
  generator, no foam tank) are not requirements and are not in the keys.
- The variant is the one for the product being bought even when a knockout makes the tender a no-bid
  (gleiswerk 03, 05 and 06; brandt 06). It is `null` only when no variant fits.

Nobody changes the agents to pass this set. Its first run goes in `reports/heldout/v1/first_run.json`
and is never rewritten.
