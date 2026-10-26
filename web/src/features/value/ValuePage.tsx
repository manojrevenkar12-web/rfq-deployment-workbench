import { useState } from "react";

import type { AgentId, Assumptions, Deployment, Discovery, Level, ValueCase } from "../../shared/api/types";
import { LeadTimeStrip } from "../../shared/charts/LeadTimeStrip";
import { days, eur, hours, int, people, role } from "../../shared/lib/format";
import { useDebounced } from "../../shared/lib/useDebounced";
import { AGENT_ORDER, AGENT_SHORT, LEVEL } from "../../shared/theme/tokens";
import {
  Button,
  ErrorState,
  Figure,
  QueryView,
  Section,
  SkeletonBlock,
  Table,
  Tag,
  ui,
} from "../../shared/ui";
import { useDeployment } from "../customer/api";
import { useCid } from "../customer/CustomerLayout";
import { useDiscovery } from "../process/api";
import { useReadiness } from "../readiness/api";
import { type AssumptionEdits, useSaveAssumptions, useValue } from "./api";
import styles from "./Value.module.css";

function Scope({
  scope,
  agreed,
  levels,
  onChange,
}: {
  scope: AgentId[];
  agreed: AgentId[];
  levels: Partial<Record<AgentId, Level>>;
  onChange: (s: AgentId[] | undefined) => void;
}) {
  const on = new Set(scope);
  const toggle = (a: AgentId) => {
    const next = AGENT_ORDER.filter((x) => (x === a ? !on.has(x) : on.has(x)));
    const same = next.length === agreed.length && next.every((x) => agreed.includes(x));
    onChange(same ? undefined : next);
  };
  return (
    <fieldset className={styles.fieldset}>
      <legend>Agents in scope</legend>
      {AGENT_ORDER.map((a) => {
        const level = levels[a] ?? "not_enough_evidence";
        return (
          <label key={a} className={styles.check}>
            <input type="checkbox" checked={on.has(a)} onChange={() => toggle(a)} />
            <span>{AGENT_SHORT[a]}</span>
            <Tag tone={LEVEL[level].tone}>{LEVEL[level].label}</Tag>
          </label>
        );
      })}
      <p className={styles.hint}>
        An agent that is not yet ready changes nothing in the case, in scope or not.
      </p>
    </fieldset>
  );
}

function NumberField({
  label,
  value,
  onChange,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  suffix?: string;
}) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      <span className={styles.inputRow}>
        <input
          className={ui.input}
          type="number"
          inputMode="decimal"
          aria-label={label}
          min={0}
          step={step}
          value={Number.isFinite(value) ? value : ""}
          onChange={(e) => onChange(e.target.valueAsNumber)}
        />
        {suffix && <span className={styles.suffix}>{suffix}</span>}
      </span>
    </label>
  );
}

function AssumptionsForm({
  base,
  edits,
  onChange,
}: {
  base: Assumptions;
  edits: AssumptionEdits;
  onChange: (e: AssumptionEdits) => void;
}) {
  const a = {
    ...base,
    ...edits,
    hourly_cost: { ...base.hourly_cost, ...(edits.hourly_cost ?? {}) },
  };
  const setRate = (r: string, v: number) =>
    onChange({ ...edits, hourly_cost: { ...(edits.hourly_cost ?? {}), [r]: v } });
  return (
    <fieldset className={styles.fieldset}>
      <legend>Assumptions</legend>
      {Object.entries(a.hourly_cost).map(([r, rate]) => (
        <NumberField
          key={r}
          label={`${role(r)}, cost per hour`}
          value={rate}
          suffix="EUR"
          onChange={(v) => setRate(r, v)}
        />
      ))}
      <NumberField
        label="Working hours per person a year"
        value={a.hours_per_person_year}
        step={10}
        onChange={(v) => onChange({ ...edits, hours_per_person_year: v })}
      />
      <NumberField
        label="Annual fee"
        value={a.annual_fee}
        step={1000}
        suffix="EUR"
        onChange={(v) => onChange({ ...edits, annual_fee: v })}
      />
      <NumberField
        label="Growth in tenders a year"
        value={Math.round(a.volume_growth * 100)}
        suffix="%"
        onChange={(v) => onChange({ ...edits, volume_growth: v / 100 })}
      />
    </fieldset>
  );
}

function Result({ v, d }: { v: ValueCase; d: Discovery | undefined }) {
  const external = new Set(
    (d?.activities ?? []).filter((a) => a.waiting_kind === "external").map((a) => a.activity),
  );
  const lt = v.lead_time_days;
  return (
    <div className={styles.result}>
      <p className={styles.statement}>{v.statement}</p>
      <div className={styles.figures}>
        <Figure compact value={int(v.hours_per_year)} label="hours back a year" />
        <Figure compact value={people(v.capacity_people)} label="of capacity" />
        <Figure compact value={eur(v.gross_per_year)} label="worth a year" />
        <Figure compact value={eur(v.net_per_year)} label="after the fee" />
        <Figure
          compact
          value={v.payback_months == null ? "never" : `${v.payback_months} months`}
          label="to pay back the fee"
        />
      </div>
      <Section
        title="The average tender with this scope"
        lead={`Half of all bids leave within ${days(lt.after)} instead of ${days(lt.before)}: between ${days(lt.saved_low)} and ${days(lt.saved_high)} faster in 90 % of resamples.`}
      >
        <LeadTimeStrip
          rows={v.what_if.timeline}
          mode="after"
          external={external}
          caption="The average tender with this scope"
        />
      </Section>
      <Section title="By role">
        <Table caption="Value by role">
          <thead>
            <tr>
              <th>Role</th>
              <th className={ui.num}>Hours a year</th>
              <th className={ui.num}>Cost per hour</th>
              <th className={ui.num}>Value</th>
              <th className={ui.num}>People</th>
            </tr>
          </thead>
          <tbody>
            {v.by_role.map((r) => (
              <tr key={r.role}>
                <td>{role(r.role)}</td>
                <td className={ui.num}>{hours(r.hours)}</td>
                <td className={ui.num}>{eur(r.rate)}</td>
                <td className={ui.num}>{eur(r.value)}</td>
                <td className={ui.num}>{r.people}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Section>
      <p className={styles.hint}>
        Hours come from replaying {int(v.what_if.period_days)} days of the customer's own quote process with
        each activity's work cut by the agents' readiness; the replay reproduces the observed median (
        {days(v.what_if.model_check.observed_median_days)} observed,{" "}
        {days(v.what_if.model_check.replayed_median_days)} replayed). The effort each agent takes off an
        activity, per readiness level, is in config/agents.yaml.
      </p>
    </div>
  );
}

function Workbench({ cid, d }: { cid: string; d: Deployment }) {
  const [scope, setScope] = useState<AgentId[] | undefined>(undefined);
  const [edits, setEdits] = useState<AssumptionEdits>({});
  const settled = useDebounced(edits);
  const clean = Object.fromEntries(
    Object.entries(settled).filter(([, x]) => (typeof x === "number" ? Number.isFinite(x) : true)),
  ) as AssumptionEdits;
  const v = useValue(cid, scope, clean);
  const disc = useDiscovery(cid);
  const ready = useReadiness(cid);
  const save = useSaveAssumptions(cid);
  const levels = Object.fromEntries(
    Object.entries(ready.data?.readiness ?? {}).map(([k, r]) => [k, r.level]),
  ) as Partial<Record<AgentId, Level>>;
  const dirty = scope !== undefined || Object.keys(edits).length > 0;

  return (
    <div className={styles.layout}>
      <aside className={styles.controls} aria-label="Scope and assumptions">
        <Scope scope={scope ?? d.scope} agreed={d.scope} levels={levels} onChange={setScope} />
        {v.data && <AssumptionsForm base={v.data.assumptions} edits={edits} onChange={setEdits} />}
        <div className={styles.buttons}>
          <Button
            variant="primary"
            disabled={Object.keys(clean).length === 0}
            busy={save.isPending}
            onClick={() =>
              save.mutate(clean, {
                onSuccess: () => setEdits({}),
              })
            }
          >
            Save assumptions for {d.customer.name.split(" ")[0]}
          </Button>
          <Button
            variant="quiet"
            disabled={!dirty}
            onClick={() => {
              setScope(undefined);
              setEdits({});
            }}
          >
            Back to the agreed case
          </Button>
        </div>
        {save.isError && <ErrorState error={save.error} onRetry={() => save.reset()} />}
        {save.isSuccess && !dirty && (
          <p role="status" className={styles.hint}>
            Saved. The overview, the SteerCo pack and the portfolio use these assumptions now.
          </p>
        )}
      </aside>
      <div aria-busy={v.isFetching} className={styles.main} data-stale={v.isPlaceholderData}>
        <QueryView query={v} skeleton={<SkeletonBlock label="Working out the value case" rows={5} />}>
          {(x) => <Result v={x} d={disc.data} />}
        </QueryView>
      </div>
    </div>
  );
}

export function ValuePage() {
  const cid = useCid();
  const d = useDeployment(cid);
  return (
    <QueryView query={d} skeleton={<SkeletonBlock label="Loading the value case" rows={5} />}>
      {(dep) => <Workbench cid={cid} d={dep} />}
    </QueryView>
  );
}
