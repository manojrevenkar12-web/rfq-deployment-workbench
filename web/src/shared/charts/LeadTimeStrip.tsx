import { motion, useReducedMotion } from "framer-motion";

import type { TimelineRow } from "../api/types";
import { days } from "../lib/format";
import { MOTION } from "../theme/tokens";
import styles from "./LeadTimeStrip.module.css";

export type StripMode = "before" | "after";

interface Segment {
  key: string;
  activity: string;
  kind: "work" | "queue" | "external";
  days: number;
}

const KIND_WORDS: Record<Segment["kind"], string> = {
  work: "working on",
  queue: "waiting for",
  external: "waiting on the buyer for",
};

function segments(rows: TimelineRow[], mode: StripMode, external: Set<string>): Segment[] {
  return rows.flatMap((r) => [
    {
      key: `${r.activity}:wait`,
      activity: r.activity,
      kind: external.has(r.activity) ? ("external" as const) : ("queue" as const),
      days: r[mode].wait,
    },
    { key: `${r.activity}:work`, activity: r.activity, kind: "work" as const, days: r[mode].work },
  ]);
}

function ticks(total: number): number[] {
  const step = total > 30 ? 10 : total > 12 ? 5 : total > 5 ? 2 : 1;
  return Array.from({ length: Math.floor(total / step) + 1 }, (_, i) => i * step);
}

/**
 * Where the average tender's calendar days go: working (solid), waiting in an internal queue (hatched) and
 * waiting on the buyer (yellow hatch). Both modes share one scale, so "with the agents" is visibly shorter
 * than the dashed outline of today. The first draw runs left to right once; switching modes resizes.
 */
export function LeadTimeStrip({
  rows,
  mode,
  external,
  caption,
}: {
  rows: TimelineRow[];
  mode: StripMode;
  external: Set<string>;
  caption: string;
}) {
  const reduce = useReducedMotion();
  const scale = rows.reduce((s, r) => s + r.before.work + r.before.wait, 0) || 1;
  const segs = segments(rows, mode, external).filter((s) => s.days > 0);
  const total = segs.reduce((s, x) => s + x.days, 0);
  const longest = segs.filter((s) => s.kind !== "work").sort((a, b) => b.days - a.days)[0];
  let offset = 0;
  const positions = new Map<string, number>();
  for (const s of segs) {
    positions.set(s.key, offset);
    offset += s.days;
  }
  const at = longest ? (((positions.get(longest.key) ?? 0) + longest.days / 2) / scale) * 100 : 0;
  const move = { duration: reduce ? 0 : MOTION.move, ease: MOTION.ease };

  return (
    <figure className={styles.figure}>
      <figcaption className="visually-hidden">{caption}</figcaption>
      <div className={styles.annotation} aria-hidden>
        {longest && (
          <motion.p
            className={[styles.callout, at > 60 && styles.flip].filter(Boolean).join(" ")}
            animate={{ left: `${at}%` }}
            initial={false}
            transition={move}
          >
            <strong>{days(longest.days)}</strong>
            {longest.kind === "external"
              ? "waiting on the buyer"
              : `${KIND_WORDS[longest.kind]} ${longest.activity.toLowerCase()}`}
          </motion.p>
        )}
      </div>
      <div className={styles.track}>
        {mode === "after" && <span className={styles.ghost} aria-hidden />}
        <motion.div
          className={styles.strip}
          animate={{ width: `${(total / scale) * 100}%` }}
          initial={reduce ? false : { width: "0%" }}
          transition={{ duration: reduce ? 0 : MOTION.draw, ease: MOTION.ease }}
          role="img"
          aria-label={`${caption}: ${days(total)} for the average tender`}
        >
          {segs.map((s) => (
            <motion.span
              key={s.key}
              className={`${styles.segment} ${styles[s.kind]}`}
              title={`${s.activity}: ${KIND_WORDS[s.kind]} it, ${days(s.days)}`}
              initial={false}
              animate={{ width: `${(s.days / total) * 100}%` }}
              transition={move}
            />
          ))}
        </motion.div>
      </div>
      <div className={styles.axis} aria-hidden>
        {ticks(scale).map((t) => (
          <span key={t} className={styles.tick} style={{ left: `${(t / scale) * 100}%` }}>
            {t === 0 ? "0 days" : t}
          </span>
        ))}
      </div>
      <ul className={styles.legend}>
        <li>
          <span className={`${styles.key} ${styles.work}`} aria-hidden /> Working
        </li>
        <li>
          <span className={`${styles.key} ${styles.queue}`} aria-hidden /> Waiting for a colleague
        </li>
        <li>
          <span className={`${styles.key} ${styles.external}`} aria-hidden /> Waiting on the buyer
        </li>
      </ul>
      <table className="visually-hidden">
        <caption>{caption}, days per tender</caption>
        <thead>
          <tr>
            <th>Activity</th>
            <th>Waiting</th>
            <th>Working</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.activity}>
              <td>{r.activity}</td>
              <td>{days(r[mode].wait, 2)}</td>
              <td>{days(r[mode].work, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
