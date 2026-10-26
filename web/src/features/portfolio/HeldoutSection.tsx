import type { Portfolio } from "../../shared/api/types";
import { date, humanise, pct } from "../../shared/lib/format";
import { EmptyState, QueryView, Section, SkeletonBlock, Table, ui } from "../../shared/ui";
import { type HeldoutSet, useHeldout } from "../../shared/api/heldout";
import styles from "./Portfolio.module.css";

const MEASURES = [
  ["requirement_recall", "Requirements found"],
  ["red_flag_recall", "Red flags found"],
  ["verdict_accuracy", "Answers right"],
  ["bid_accuracy", "Bid / no-bid right"],
  ["unsafe_bid_avoided", "No bid where the customer would not"],
] as const;

function rate(m: { right: number; of: number } | undefined) {
  return m ? `${pct(m.right / Math.max(1, m.of))} (${m.right} of ${m.of})` : "n/a";
}

function causes(s: HeldoutSet) {
  const by = new Map<string, number>();
  let total = 0;
  for (const c of Object.values(s.customers))
    for (const m of c.misses) {
      const key = `${m.owner}: ${m.cause}`;
      by.set(key, (by.get(key) ?? 0) + m.count);
      total += m.count;
    }
  return { total, rows: [...by.entries()].sort((a, b) => b[1] - a[1]) };
}

function SetView({ s, p }: { s: HeldoutSet; p: Portfolio }) {
  const names = Object.fromEntries(p.customers.map((c) => [c.id, c.name]));
  const ids = Object.keys(s.customers);
  const c = causes(s);
  return (
    <>
      <Table caption={`Held-out set ${s.set}, first run`}>
        <thead>
          <tr>
            <th>Measure</th>
            {ids.map((id) => (
              <th key={id} className={ui.num}>
                {names[id] ?? id}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MEASURES.map(([key, label]) => (
            <tr key={key}>
              <td>{label}</td>
              {ids.map((id) => (
                <td key={id} className={ui.num}>
                  {rate(s.customers[id]?.metrics[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
      <div className={styles.causes}>
        <h3>Where the {c.total} misses come from</h3>
        <ul>
          {c.rows.map(([k, n]) => (
            <li key={k}>
              <span>{humanise(k)}</span>
              <span className={styles.causeTrack} aria-hidden>
                <span
                  className={styles.causeBar}
                  style={{ inlineSize: `${(n / Math.max(1, c.total)) * 100}%` }}
                />
              </span>
              <span className={ui.num}>{n}</span>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

/** The honest test: first runs on tenders written by someone who never saw the agents' code. */
export function HeldoutSection({ p }: { p: Portfolio }) {
  const q = useHeldout();
  return (
    <QueryView
      query={q}
      skeleton={<SkeletonBlock label="Loading the held-out results" rows={3} />}
      isEmpty={(sets) => sets.length === 0}
      empty={
        <EmptyState title="No held-out set yet">
          Have someone who has not seen the code write tenders from heldout/WRITING_TENDERS.md, then run rdw
          heldout &lt;set&gt;. Until then every score here is on tenders the agents were built against.
        </EmptyState>
      }
    >
      {(sets) => {
        const s = sets.find((x) => x.status === "heldout") ?? sets[sets.length - 1];
        if (!s) return null;
        return (
          <Section
            title="On tenders nobody who built the agents has seen"
            lead={`Held-out set ${s.set}, first run on ${date(s.run_at)}, recorded once and never rewritten. The scores above are on the customers' past tenders, which the agents were built against; these are the ones to quote.`}
          >
            <SetView s={s} p={p} />
          </Section>
        );
      }}
    </QueryView>
  );
}
