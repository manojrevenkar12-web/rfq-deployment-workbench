import { useState } from "react";

import type { AgentId, Miss, Readiness } from "../../shared/api/types";
import { humanise, pct, value } from "../../shared/lib/format";
import { AGENT_ORDER, LEVEL } from "../../shared/theme/tokens";
import {
  EmptyState,
  Notice,
  QueryView,
  ReadinessMeter,
  Section,
  SkeletonBlock,
  Table,
  Tag,
  ui,
} from "../../shared/ui";
import { Segmented } from "../../shared/ui/Segmented";
import { useHeldout } from "../../shared/api/heldout";
import { useDeployment } from "../customer/api";
import { useCid } from "../customer/CustomerLayout";
import { useReadiness } from "./api";
import styles from "./Readiness.module.css";

function Agents({ r, scope }: { r: Readiness; scope: Set<AgentId> }) {
  return (
    <Section
      title="Agents"
      lead={`An agent works on its own when the lower bound of its ${pct(r.bar.confidence)} interval clears ${pct(r.bar.automate)}, and assists a person from ${pct(r.bar.assist)}. The bar shows the lower bound, the tick the plain score, the dashes the two bars.`}
    >
      <ol className={styles.agents}>
        {AGENT_ORDER.map((id) => {
          const a = r.readiness[id];
          if (!a) return null;
          const level = LEVEL[a.level];
          return (
            <li key={id} className={styles.agent}>
              <div className={styles.agentHead}>
                <h3>{a.label}</h3>
                <Tag tone={level.tone} title={level.long}>
                  {level.label}
                </Tag>
                {!scope.has(id) && <span className={styles.out}>Not in scope</span>}
              </div>
              <p className={styles.soft}>{a.does}</p>
              <ReadinessMeter
                lowerBound={a.lower_bound}
                rate={a.rate}
                tone={level.tone}
                marks={[r.bar.assist, r.bar.automate]}
                label={`${a.label} readiness`}
              />
              <p className={styles.numbers}>
                {humanise(a.metric)}: {a.right} of {a.of} ({pct(a.rate, 1)}), lower bound{" "}
                {pct(a.lower_bound, 1)}.
                {a.misses > 0 &&
                  ` ${a.misses} misses: ${a.fix_in_deployment} for the deployment, ${a.fix_in_platform} for the platform.`}
              </p>
            </li>
          );
        })}
      </ol>
    </Section>
  );
}

function Metrics({ r }: { r: Readiness }) {
  return (
    <Section title="Every measure">
      <Table caption="Scores against the customer's past decisions">
        <thead>
          <tr>
            <th>Measure</th>
            <th className={ui.num}>Right</th>
            <th className={ui.num}>Score</th>
            <th className={ui.num}>Lower bound</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(r.metrics).map(([k, m]) => (
            <tr key={k}>
              <td>{humanise(k)}</td>
              <td className={ui.num}>
                {m.right} of {m.of}
              </td>
              <td className={ui.num}>{pct(m.rate, 1)}</td>
              <td className={ui.num}>{pct(m.lower_bound, 1)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

function describe(x: unknown, labels: Record<string, string>): string {
  if (x == null) return "nothing";
  if (typeof x === "object" && !Array.isArray(x)) {
    const o = x as { kind?: string; value?: unknown; verdict?: string };
    const kind = o.kind && (labels[o.kind] ?? humanise(o.kind));
    return [kind, o.value != null && value(o.value), o.verdict].filter(Boolean).join(", ");
  }
  return labels[String(x)] ?? humanise(String(x));
}

function Misses({ misses, labels }: { misses: Miss[]; labels: Record<string, string> }) {
  const deployment = misses.filter((m) => m.owner === "deployment");
  const platform = misses.filter((m) => m.owner === "platform");
  const [owner, setOwner] = useState<"deployment" | "platform">(
    deployment.length || !platform.length ? "deployment" : "platform",
  );
  const shown = owner === "deployment" ? deployment : platform;
  return (
    <Section
      title="Where the agents disagree with past decisions"
      lead="The cause decides who fixes it: a capability or norm profile is deployment work, vocabulary and rules are platform work."
      actions={
        <Segmented
          label="Show misses for"
          value={owner}
          onChange={setOwner}
          options={[
            { value: "deployment", label: `Deployment (${deployment.length})` },
            { value: "platform", label: `Platform (${platform.length})` },
          ]}
        />
      }
    >
      {shown.length === 0 ? (
        <p className={styles.soft}>
          {owner === "deployment"
            ? "No miss is explained by this customer's profiles."
            : "No miss belongs to the platform on these tenders. They were used to build the agents; see the held-out set for the honest test."}
        </p>
      ) : (
        <ul className={styles.misses}>
          {shown.map((m, i) => (
            <li key={`${m.tender}-${i}`}>
              <span className={styles.soft}>
                {m.tender}, {humanise(m.agent)}, {humanise(m.cause)}
              </span>
              <blockquote className={ui.quote}>{m.text}</blockquote>
              <p className={styles.soft}>
                Past decision: {describe(m.expected, labels)}. Agents: {describe(m.got, labels)}.
              </p>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

const QUOTE = [
  ["requirement_recall", "requirements found"],
  ["red_flag_recall", "red flags found"],
  ["verdict_accuracy", "answers right"],
  ["bid_accuracy", "bid decisions right"],
] as const;

/** The scores below are on tenders the agents were built against; the held-out first run is the honest one. */
function HeldoutNote({ cid }: { cid: string }) {
  const q = useHeldout();
  const set = q.data?.find((s) => s.status === "heldout");
  const c = set?.customers[cid];
  if (!set || !c) return null;
  const parts = QUOTE.flatMap(([k, label]) => {
    const m = c.metrics[k];
    return m ? [`${pct(m.right / Math.max(1, m.of))} ${label}`] : [];
  });
  return (
    <Notice>
      These tenders were used to build the agents, so expect near-perfect scores. On {c.tenders} held-out
      tenders written by someone who never saw the code (set {set.set}, first run): {parts.join(", ")}. Quote
      those.
    </Notice>
  );
}

export function ReadinessPage() {
  const cid = useCid();
  const q = useReadiness(cid);
  const d = useDeployment(cid);
  const scope = new Set<AgentId>(d.data?.scope ?? AGENT_ORDER);
  return (
    <QueryView
      query={q}
      skeleton={<SkeletonBlock label="Scoring the agents" rows={6} height="var(--space-8)" />}
      isEmpty={(r) => r.tenders === 0}
      empty={
        <EmptyState title="Nothing scored yet">
          Readiness needs the customer's past tenders with their compliance matrices and bid decisions.
          Without them every agent stays at too few tenders.
        </EmptyState>
      }
    >
      {(r) => (
        <>
          <p className={styles.intro}>
            Scored on {r.tenders} past tenders against the customer's own compliance matrices and bid
            decisions.
          </p>
          <HeldoutNote cid={cid} />
          <Agents r={r} scope={scope} />
          <Misses misses={r.misses} labels={r.kind_labels} />
          <Metrics r={r} />
        </>
      )}
    </QueryView>
  );
}
