import { useState } from "react";

import type { Discovery, LiveComparison, ValueCase } from "../../shared/api/types";
import { LeadTimeStrip, type StripMode } from "../../shared/charts/LeadTimeStrip";
import { days, hours, int, pct, role } from "../../shared/lib/format";
import { EmptyState, Figure, QueryView, Section, SkeletonBlock, Table, Tag, ui } from "../../shared/ui";
import { Segmented } from "../../shared/ui/Segmented";
import { useDeployment } from "../customer/api";
import { useCid } from "../customer/CustomerLayout";
import { useValue } from "../value/api";
import { useDiscovery, useLive } from "./api";
import styles from "./Process.module.css";

function headline(d: Discovery) {
  const b = d.bottleneck;
  const where = !b
    ? ""
    : b.kind === "external"
      ? ` The longest wait is for the buyer's answers: ${days(b.wait_hours_per_case / 24)} per tender, outside the company's hands.`
      : ` The longest wait is the queue before ${b.activity.toLowerCase()}: ${days(b.wait_hours_per_case / 24)} per tender.`;
  return `Half of all bids leave within ${days(d.lead_time_days.median)} of the request; one in five takes longer than ${days(d.lead_time_days.p80)}.${where}`;
}

function Hero({ d, v }: { d: Discovery; v: ValueCase | undefined }) {
  const [mode, setMode] = useState<StripMode>("before");
  const external = new Set(d.activities.filter((a) => a.waiting_kind === "external").map((a) => a.activity));
  return (
    <section className={styles.hero} aria-labelledby="where-time-goes">
      <div className={styles.heroHead}>
        <div>
          <h2 id="where-time-goes">Where a tender's days go</h2>
          <p className={styles.lead}>{headline(d)}</p>
        </div>
        <Segmented
          label="Show the process"
          value={mode}
          onChange={setMode}
          options={[
            { value: "before", label: "Today" },
            { value: "after", label: "With the agents in scope" },
          ]}
        />
      </div>
      {v ? (
        <>
          <LeadTimeStrip
            rows={v.what_if.timeline}
            mode={mode}
            external={external}
            caption={
              mode === "before" ? "The average tender today" : "The average tender with the agents in scope"
            }
          />
          <p className={styles.note}>
            Replayed from the CRM export: the same tenders, people and buyer delays, with each activity's work
            scaled by the agents' readiness. The replay reproduces the observed median (
            {days(v.what_if.model_check.observed_median_days)} observed,{" "}
            {days(v.what_if.model_check.replayed_median_days)} replayed). With the agents, half of all bids
            would leave within {days(v.lead_time_days.after)}.
          </p>
        </>
      ) : (
        <SkeletonBlock label="Replaying the process" rows={1} height="var(--strip-height)" />
      )}
    </section>
  );
}

function Activities({ d }: { d: Discovery }) {
  return (
    <Section title="Activities" lead="Sorted by how long a tender waits before each one.">
      <Table caption="Activities in the quote process">
        <thead>
          <tr>
            <th>Activity</th>
            <th>Who</th>
            <th className={ui.num}>Times per tender</th>
            <th className={ui.num}>Work each time</th>
            <th className={ui.num}>Waiting per tender</th>
            <th>Waiting for</th>
          </tr>
        </thead>
        <tbody>
          {d.activities.map((a) => (
            <tr key={a.activity}>
              <td>{a.activity}</td>
              <td>{role(a.role)}</td>
              <td className={ui.num}>
                {a.share_of_cases.toLocaleString("en-GB", { maximumFractionDigits: 2 })}
              </td>
              <td className={ui.num}>{hours(a.work_hours_mean, 1)}</td>
              <td className={ui.num}>{hours(a.wait_hours_per_case, 1)}</td>
              <td>{a.waiting_kind === "external" ? "the buyer" : "a colleague"}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

function Utilisation({ d }: { d: Discovery }) {
  const busy = new Set(d.busy_roles ?? []);
  const rows = Object.entries(d.utilisation).sort((a, b) => b[1] - a[1]);
  return (
    <Section title="Who is busy" lead="Hours of quote work against a 40-hour week, over the whole export.">
      <ul className={styles.bars}>
        {rows.map(([r, u]) => (
          <li key={r}>
            <span className={styles.barLabel}>
              {role(r)}
              <span className={styles.soft}>
                {" "}
                {d.people[r] ?? 0} {d.people[r] === 1 ? "person" : "people"}
              </span>
            </span>
            <span className={styles.barTrack} aria-hidden>
              <span
                className={styles.barFill}
                style={{ width: `${Math.min(1, u) * 100}%` }}
                data-high={busy.has(r)}
              />
            </span>
            <span className={ui.num}>{pct(u)}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Variants({ d }: { d: Discovery }) {
  return (
    <Section
      title="The ways a tender goes"
      lead={`The five most common paths, of ${int(d.cases)} tenders. ${pct(d.rework_share)} go round at least one step twice.`}
    >
      <ol className={styles.variants}>
        {d.variants.map((v, i) => (
          <li key={i}>
            <span className={styles.count}>{pct(v.count / d.cases)}</span>
            <ol className={styles.path} aria-label={`Path taken by ${v.count} tenders`}>
              {v.path.map((step, k) => (
                <li key={k}>{step}</li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </Section>
  );
}

function Live({ live }: { live: LiveComparison }) {
  return (
    <Section
      title="Since go-live"
      lead={`${live.discovery.cases} tenders since ${live.since}: half of all bids now leave within ${days(live.discovery.lead_time_days.median)}, against ${days(live.projected.lead_time_days.after)} projected.`}
    >
      <Table caption="Effort per activity since go-live">
        <thead>
          <tr>
            <th>Activity</th>
            <th className={ui.num}>Hours before</th>
            <th className={ui.num}>Hours now</th>
            <th className={ui.num}>Planned</th>
            <th className={ui.num}>Now</th>
            <th>Adoption</th>
          </tr>
        </thead>
        <tbody>
          {live.activities.map((a) => (
            <tr key={a.activity}>
              <td>{a.activity}</td>
              <td className={ui.num}>{a.hours_before}</td>
              <td className={ui.num}>{a.hours_after}</td>
              <td className={ui.num}>{pct(a.projected_factor)}</td>
              <td className={ui.num}>{pct(a.actual_factor)}</td>
              <td>
                {a.status === "no_agent" ? (
                  <Tag tone="quiet">No agent here</Tag>
                ) : a.status === "behind" ? (
                  <Tag tone="bad">Behind the plan</Tag>
                ) : (
                  <Tag tone="good">As planned</Tag>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

export function ProcessPage() {
  const cid = useCid();
  const q = useDiscovery(cid);
  const v = useValue(cid);
  const dep = useDeployment(cid);
  const live = useLive(cid, dep.data?.live === true);
  return (
    <QueryView
      query={q}
      skeleton={<SkeletonBlock label="Reading the quote process" rows={4} />}
      isEmpty={(d) => d.cases === 0}
      empty={
        <EmptyState title="No quote process yet">
          Ask the customer for the CRM export of quote activities (case, activity, person, start, end) and put
          it in data/customers/{cid}/quote_process.csv.
        </EmptyState>
      }
    >
      {(d) => (
        <>
          <Hero d={d} v={v.data} />
          <div className={styles.figures}>
            <Figure value={int(d.cases)} label={`tenders in ${d.period_days} days`} />
            <Figure value={pct(d.submitted / d.cases)} label="answered with a bid" />
            <Figure value={days(d.lead_time_days.median)} label="median request to bid" />
            <Figure value={pct(d.rework_share)} label="go round a step twice" />
          </div>
          {live.data && <Live live={live.data} />}
          <Activities d={d} />
          <div className={styles.split}>
            <Utilisation d={d} />
            <Variants d={d} />
          </div>
        </>
      )}
    </QueryView>
  );
}
