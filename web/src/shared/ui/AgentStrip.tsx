import type { AgentId, Level } from "../api/types";
import { AGENT_ORDER, AGENT_SHORT, LEVEL } from "../theme/tokens";
import styles from "./AgentStrip.module.css";

/**
 * Six squares, one per agent in the order a tender passes through them. Filled by readiness level; an agent
 * the customer has not put in scope is drawn as an outline, whatever its score.
 */
export function AgentStrip({
  readiness,
  scope,
}: {
  readiness: Partial<Record<AgentId, Level>>;
  scope: AgentId[];
}) {
  const inScope = new Set(scope);
  return (
    <ul className={styles.strip} aria-label="Agents">
      {AGENT_ORDER.map((a) => {
        const level = readiness[a] ?? "not_enough_evidence";
        const on = inScope.has(a);
        const text = `${AGENT_SHORT[a]}: ${LEVEL[level].label.toLowerCase()}${on ? "" : ", not in scope"}`;
        return (
          <li
            key={a}
            className={[styles.cell, styles[LEVEL[level].tone], !on && styles.out].filter(Boolean).join(" ")}
            title={text}
          >
            <span className="visually-hidden">{text}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function AgentStripLegend() {
  return (
    <ul className={styles.legend}>
      <li>
        <span className={`${styles.cell} ${styles.good}`} aria-hidden /> Works on its own
      </li>
      <li>
        <span className={`${styles.cell} ${styles.info}`} aria-hidden /> Assists a person
      </li>
      <li>
        <span className={`${styles.cell} ${styles.bad}`} aria-hidden /> Not yet
      </li>
      <li>
        <span className={`${styles.cell} ${styles.good} ${styles.out}`} aria-hidden /> Not in scope
      </li>
    </ul>
  );
}
