import { AnimatePresence, motion } from "framer-motion";
import { type FormEvent, useState } from "react";

import type { AgentId, Deployment, Kpi, Milestone } from "../../shared/api/types";
import { date, humanise, kpi } from "../../shared/lib/format";
import { AGENT_SHORT, KPI_STATUS, MOTION } from "../../shared/theme/tokens";
import { Button, ErrorState, QueryView, Section, SkeletonBlock, Table, Tag, ui } from "../../shared/ui";
import { Markdown } from "../../shared/ui/Markdown";
import { useDeployment, useRecordDecision, useSteerCo } from "../customer/api";
import { useCid } from "../customer/CustomerLayout";
import styles from "./Overview.module.css";

const WHO: Record<string, string> = {
  strategist: "Strategist",
  champion: "Customer champion",
  product: "Product team",
};

function NextSteps({ d }: { d: Deployment }) {
  if (d.next_steps.length === 0)
    return (
      <Section title="Next steps">
        <p className={styles.soft}>Nothing is open: every milestone is on time and every KPI is on target.</p>
      </Section>
    );
  return (
    <Section title="Next steps" lead="Worked out from the plan, the scores and the quote process.">
      <ol className={styles.steps}>
        {d.next_steps.map((s, i) => (
          <li key={i}>
            <span className={styles.who}>{WHO[s.who] ?? humanise(s.who)}</span>
            <p>{s.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

function kpiTarget(k: Kpi) {
  return `${k.better === "higher" ? "at least" : "at most"} ${kpi(k.target, k.format)}`;
}

function Kpis({ kpis }: { kpis: Kpi[] }) {
  return (
    <Section title="KPIs agreed with the customer">
      <Table caption="KPIs">
        <thead>
          <tr>
            <th>KPI</th>
            <th>Target</th>
            <th className={ui.num}>Before</th>
            <th className={ui.num}>Now</th>
            <th>Measured on</th>
          </tr>
        </thead>
        <tbody>
          {kpis.map((k) => (
            <tr key={k.key}>
              <td>{k.label}</td>
              <td>{kpiTarget(k)}</td>
              <td className={ui.num}>{k.baseline == null ? "" : kpi(k.baseline, k.format)}</td>
              <td className={ui.num}>
                <Tag tone={KPI_STATUS[k.status]}>{kpi(k.actual, k.format)}</Tag>
              </td>
              <td className={styles.soft}>{k.basis}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

const MILESTONE_TONE = { done: "good", overdue: "bad", planned: "quiet" } as const;

function milestoneNote(m: Milestone) {
  if (m.state === "done")
    return m.days_late > 0 ? `done ${date(m.done)}, ${m.days_late} days late` : `done ${date(m.done)}`;
  if (m.state === "overdue") return `planned ${date(m.planned)}, overdue by ${m.days_late} days`;
  return `planned ${date(m.planned)}`;
}

function Milestones({ items }: { items: Milestone[] }) {
  return (
    <Section title="Plan">
      <ol className={styles.timeline}>
        {items.map((m) => (
          <li key={m.name} className={styles[m.state]}>
            <Tag tone={MILESTONE_TONE[m.state]}>{m.name}</Tag>
            <span className={styles.soft}>{milestoneNote(m)}</span>
          </li>
        ))}
      </ol>
    </Section>
  );
}

function People({ d }: { d: Deployment }) {
  return (
    <Section title="People">
      <ul className={styles.people}>
        {d.stakeholders.map((s) => (
          <li key={s.name}>
            <strong>{s.name}</strong>
            <span>
              {s.role}, {s.side}
            </span>
            <p className={styles.soft}>{s.note}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Risks({ d }: { d: Deployment }) {
  return (
    <Section title="Risks">
      {d.risks.length === 0 ? (
        <p className={styles.soft}>No risks recorded.</p>
      ) : (
        <ul className={styles.risks}>
          {d.risks.map((r) => (
            <li key={r.risk}>
              <p>{r.risk}</p>
              <p className={styles.soft}>
                {r.owner}: {r.mitigation}
              </p>
            </li>
          ))}
        </ul>
      )}
      {Object.keys(d.not_in_scope).length > 0 && (
        <>
          <h3>Left out of scope on purpose</h3>
          <ul className={styles.risks}>
            {Object.entries(d.not_in_scope).map(([agent, why]) => (
              <li key={agent}>
                <p>
                  <strong>{AGENT_SHORT[agent as AgentId] ?? humanise(agent)}</strong>: {why}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
    </Section>
  );
}

function Decisions({ cid, d }: { cid: string; d: Deployment }) {
  const record = useRecordDecision(cid);
  const [text, setText] = useState("");
  const [by, setBy] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    record.mutate(
      { decision: text.trim(), by: by.trim() },
      {
        onSuccess: () => {
          setText("");
        },
      },
    );
  };
  return (
    <Section
      title="Decisions"
      lead="What the customer decided, so nobody has to remember it at the next SteerCo."
    >
      <ul className={styles.decisions}>
        <AnimatePresence initial={false}>
          {[...d.decisions].reverse().map((x) => (
            <motion.li
              key={`${x.date}-${x.decision}`}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: MOTION.move, ease: MOTION.ease }}
            >
              <span className={styles.soft}>
                {date(x.date)}, {x.by}
              </span>
              <p>{x.decision}</p>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      <form className={styles.form} onSubmit={submit}>
        <label>
          <span>Decision</span>
          <textarea
            className={ui.input}
            rows={2}
            value={text}
            minLength={3}
            maxLength={2000}
            required
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <label>
          <span>Decided by</span>
          <input
            className={ui.input}
            value={by}
            maxLength={128}
            required
            onChange={(e) => setBy(e.target.value)}
          />
        </label>
        <Button
          type="submit"
          variant="primary"
          busy={record.isPending}
          disabled={text.trim().length < 3 || !by.trim()}
        >
          Record decision
        </Button>
        {record.isError && <ErrorState error={record.error} onRetry={() => record.reset()} />}
        {record.isSuccess && (
          <p role="status" className={styles.soft}>
            Decision recorded.
          </p>
        )}
      </form>
    </Section>
  );
}

function SteerCoPack({ cid }: { cid: string }) {
  const [open, setOpen] = useState(false);
  const q = useSteerCo(cid, open);
  const download = (markdown: string) => {
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `steerco-${cid}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Section
      title="SteerCo pack"
      lead="Status, KPIs, adoption since go-live and the asks, written from the same numbers as this page."
      actions={
        <Button onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="steerco-pack">
          {open ? "Hide pack" : "Show pack"}
        </Button>
      }
    >
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id="steerco-pack"
            key="pack"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: MOTION.move, ease: MOTION.ease }}
            className={styles.packWrap}
          >
            <div className={ui.panel}>
              <QueryView
                query={q}
                skeleton={<SkeletonBlock label="Writing the SteerCo pack" rows={6} height="var(--space-5)" />}
              >
                {(s) => (
                  <div className={styles.pack}>
                    <Button onClick={() => download(s.markdown)}>Download Markdown</Button>
                    <Markdown source={s.markdown} />
                  </div>
                )}
              </QueryView>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Section>
  );
}

export function OverviewPage() {
  const cid = useCid();
  const q = useDeployment(cid);
  return (
    <QueryView query={q} skeleton={<SkeletonBlock label="Loading the overview" rows={5} />}>
      {(d) => (
        <>
          <p className={styles.summary}>{d.summary}</p>
          <div className={styles.grid}>
            <NextSteps d={d} />
            <Milestones items={d.milestones} />
          </div>
          <Kpis kpis={d.kpis} />
          <SteerCoPack cid={cid} />
          <div className={styles.grid}>
            <Decisions cid={cid} d={d} />
            <div className={styles.stack}>
              <Risks d={d} />
              <People d={d} />
            </div>
          </div>
        </>
      )}
    </QueryView>
  );
}
