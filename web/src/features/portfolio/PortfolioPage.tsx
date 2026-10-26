import { Link } from "react-router-dom";

import type { Portfolio } from "../../shared/api/types";
import { date, days, eur, humanise, pct } from "../../shared/lib/format";
import { HEALTH, STAGE } from "../../shared/theme/tokens";
import { EmptyState, PageHeader, QueryView, Section, SkeletonBlock, Table, Tag, ui } from "../../shared/ui";
import { AgentStrip, AgentStripLegend } from "../../shared/ui/AgentStrip";
import { usePortfolio } from "./api";
import { HeldoutSection } from "./HeldoutSection";
import styles from "./Portfolio.module.css";

function lead(p: Portfolio) {
  const by = (s: string) => p.customers.filter((c) => c.stage === s).length;
  const value = p.customers.reduce((s, c) => s + c.value_per_year, 0);
  return `${p.customers.length} customers: ${by("scale")} live, ${by("pilot")} in pilot, ${by("discovery")} in discovery. At today's readiness the agents in scope are worth ${eur(value)} a year to them.`;
}

function Customers({ p }: { p: Portfolio }) {
  return (
    <Section title="Where each deployment stands" lead={<AgentStripLegend />}>
      <Table caption="Customers">
        <thead>
          <tr>
            <th>Customer</th>
            <th>Health</th>
            <th>Agents</th>
            <th className={ui.num}>Value a year</th>
            <th>Renewal</th>
            <th>Next step</th>
          </tr>
        </thead>
        <tbody>
          {p.customers.map((c) => (
            <tr key={c.id}>
              <td>
                <Link to={`/c/${c.id}`} className={styles.customer}>
                  {c.name}
                </Link>
                <span className={styles.sub}>
                  {c.industry}. {STAGE[c.stage] ?? c.stage}, {c.tenders_scored} tenders scored.
                </span>
              </td>
              <td>
                <Tag tone={HEALTH[c.health].tone}>{HEALTH[c.health].label}</Tag>
              </td>
              <td>
                <AgentStrip readiness={c.readiness} scope={c.scope} />
              </td>
              <td className={ui.num}>{eur(c.value_per_year)}</td>
              <td>{date(c.renewal)}</td>
              <td className={styles.next}>{c.next_step ?? "Nothing open."}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

function Backlog({ p }: { p: Portfolio }) {
  const fixes = p.profile_fixes.reduce<Record<string, number>>((acc, f) => {
    acc[f.customer] = (acc[f.customer] ?? 0) + 1;
    return acc;
  }, {});
  return (
    <div className={styles.split}>
      <Section
        title="For the product team"
        lead="Misses the platform has to fix: vocabulary, parsing, rules. A miss seen at two customers is a core fix."
      >
        {p.platform_backlog.length === 0 ? (
          <p className={styles.quietNote}>
            No miss on the customers' past tenders belongs to the platform, which is expected: the agents were
            built against them. The held-out set above is where the platform's work shows.
          </p>
        ) : (
          <ol className={styles.backlog}>
            {p.platform_backlog.map((b) => (
              <li key={`${b.agent}-${b.cause}-${b.kind}`}>
                <strong>
                  {humanise(b.agent)}: {humanise(b.kind)}
                </strong>
                <span>
                  {b.count} misses ({b.cause}) at {b.customers.join(", ")}
                  {b.scales ? ". Seen at more than one customer." : "."}
                </span>
                {b.examples[0] && <q className={ui.quote}>{b.examples[0]}</q>}
              </li>
            ))}
          </ol>
        )}
      </Section>
      <Section
        title="For the deployments"
        lead="Misses that a customer's capability or norm profile explains. The strategist fixes these, not the product."
      >
        {Object.keys(fixes).length === 0 ? (
          <p className={styles.quietNote}>Every profile agrees with the customers' past decisions.</p>
        ) : (
          <ul className={styles.fixes}>
            {p.customers
              .filter((c) => fixes[c.id])
              .map((c) => (
                <li key={c.id}>
                  <Link to={`/c/${c.id}/readiness`}>{c.name}</Link>
                  <span>{fixes[c.id]} answers disagree with past decisions</span>
                </li>
              ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

function Playbook({ p }: { p: Portfolio }) {
  const pb = p.playbook;
  return (
    <div className={styles.split}>
      <Section
        title="What the deployments teach"
        lead="From every customer's plan: how long the steps took, which ones slip."
      >
        <dl className={styles.facts}>
          <div>
            <dt>Kickoff to a scored pilot</dt>
            <dd>{days(pb.days_kickoff_to_scored_pilot, 0)}</dd>
          </div>
          <div>
            <dt>Kickoff to go-live</dt>
            <dd>{days(pb.days_kickoff_to_go_live, 0)}</dd>
          </div>
          <div>
            <dt>Answers confirmed unchanged</dt>
            <dd>{p.reviews.acceptance == null ? "None yet" : pct(p.reviews.acceptance)}</dd>
          </div>
        </dl>
        <Table caption="Steps that slip">
          <thead>
            <tr>
              <th>Step</th>
              <th className={ui.num}>Median days late</th>
              <th className={ui.num}>Seen</th>
            </tr>
          </thead>
          <tbody>
            {pb.late_steps.map((s) => (
              <tr key={s.step}>
                <td>{s.step}</td>
                <td className={ui.num}>{s.median_days_late}</td>
                <td className={ui.num}>{s.times}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Section>
      <Section
        title="Core or custom"
        lead="Requirement kinds every customer's tenders contain belong in the core vocabulary; the rest is deployment work."
      >
        <ul className={styles.kinds} aria-label="Shared by every customer">
          {p.shared_kinds.map((k) => (
            <li key={k}>{p.kind_labels[k] ?? humanise(k)}</li>
          ))}
        </ul>
        <ul className={styles.custom}>
          {p.customers.map((c) => (
            <li key={c.id}>
              <strong>{c.name}</strong> adds {p.customer_specific_kinds[c.id]?.length ?? 0} kinds of its own:{" "}
              {(p.customer_specific_kinds[c.id] ?? [])
                .map((k) => (p.kind_labels[k] ?? humanise(k)).toLowerCase())
                .join(", ")}
              .
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

export function PortfolioPage() {
  const q = usePortfolio();
  return (
    <>
      <PageHeader title="Deployments" lead={q.data ? lead(q.data) : "Every customer the agents work for."} />
      <QueryView
        query={q}
        skeleton={<SkeletonBlock label="Loading the deployments" rows={4} />}
        isEmpty={(p) => p.customers.length === 0}
        empty={
          <EmptyState title="No customers yet">
            Add a customer under config/customers/&lt;id&gt;/ (customer.yaml and deployment.yaml) with their
            tenders and quote-process export; rdw-sim builds three examples.
          </EmptyState>
        }
      >
        {(p) => (
          <div className={styles.page}>
            <Customers p={p} />
            <HeldoutSection p={p} />
            <Backlog p={p} />
            <Playbook p={p} />
          </div>
        )}
      </QueryView>
    </>
  );
}
