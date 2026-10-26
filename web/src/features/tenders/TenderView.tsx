import { AnimatePresence, motion } from "framer-motion";
import { type ReactNode, useMemo, useState } from "react";

import type { Requirement, Review, TenderAnalysis, Verdict } from "../../shared/api/types";
import { date, value } from "../../shared/lib/format";
import { BID, MOTION, NORM_STATUS, VERDICT } from "../../shared/theme/tokens";
import { Button, ErrorState, Section, Table, Tag, ui } from "../../shared/ui";
import { Segmented } from "../../shared/ui/Segmented";
import { reviewerName, useReview } from "./api";
import styles from "./Tender.module.css";

type Filter = "flags" | "clarify" | "all";

const VERDICTS: Verdict[] = ["comply", "clarify", "deviate"];

function ReviewControls({
  r,
  review,
  reviewer,
  onReview,
  busy,
}: {
  r: Requirement;
  review: Review | undefined;
  reviewer: string;
  onReview: (verdict: Verdict) => void;
  busy: boolean;
}) {
  if (review)
    return (
      <motion.p
        className={styles.reviewed}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: MOTION.quick }}
      >
        {review.action === "confirm"
          ? `Confirmed by ${review.reviewer}`
          : `Changed to ${VERDICT[review.verdict].label.toLowerCase()} by ${review.reviewer}`}
      </motion.p>
    );
  const disabled = !reviewer.trim() || busy;
  return (
    <div className={styles.reviewButtons} role="group" aria-label={`Review ${r.id}`}>
      <Button variant="primary" disabled={disabled} onClick={() => onReview(r.verdict)}>
        Confirm
      </Button>
      {VERDICTS.filter((v) => v !== r.verdict).map((v) => (
        <Button key={v} disabled={disabled} onClick={() => onReview(v)}>
          Change to {VERDICT[v].label.toLowerCase()}
        </Button>
      ))}
    </div>
  );
}

function RequirementRow({
  r,
  review,
  reviewer,
  onReview,
  busy,
  readOnly,
}: {
  r: Requirement;
  review: Review | undefined;
  reviewer: string;
  onReview: (verdict: Verdict) => void;
  busy: boolean;
  readOnly: boolean;
}) {
  const shown = review?.verdict ?? r.verdict;
  return (
    <motion.li
      layout
      className={styles.req}
      data-verdict={shown}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: MOTION.quick }}
    >
      <div className={styles.source}>
        <span className={styles.locator}>
          {r.source.file}, {r.source.locator}
        </span>
        <blockquote className={ui.quote}>{r.source.text}</blockquote>
      </div>
      <div className={styles.reading}>
        <div className={styles.verdictLine}>
          <Tag tone={VERDICT[shown].tone}>{VERDICT[shown].label}</Tag>
          {r.red_flag && <span className={styles.flag}>Red flag{r.severity ? `, ${r.severity}` : ""}</span>}
        </div>
        <p>
          <strong>{r.label}</strong>
          {r.kind !== "procedural" && r.kind !== "other" && <>: {value(r.value, r.unit)}</>}
          <span className={styles.soft}>
            {" "}
            ({r.priority === "mandatory" ? "must" : r.priority === "desirable" ? "should" : "for information"}
            )
          </span>
        </p>
        <p className={styles.soft}>{r.reason}</p>
        {!readOnly && (
          <ReviewControls r={r} review={review} reviewer={reviewer} onReview={onReview} busy={busy} />
        )}
      </div>
    </motion.li>
  );
}

function Requirements({ t, cid, readOnly }: { t: TenderAnalysis; cid: string; readOnly: boolean }) {
  const flags = t.requirements.filter((r) => r.red_flag).length;
  const [filter, setFilter] = useState<Filter>(flags > 0 ? "flags" : "all");
  const [reviewer, setReviewer] = useState(reviewerName.get);
  const review = useReview(cid, t.tender_id);
  const reviews = useMemo(() => new Map((t.reviews ?? []).map((x) => [x.requirement, x])), [t.reviews]);
  const shown = t.requirements.filter((r) =>
    filter === "flags" ? r.red_flag : filter === "clarify" ? r.verdict !== "comply" : true,
  );
  const reviewedCount = t.requirements.filter((r) => reviews.has(r.id)).length;

  return (
    <Section
      title="Requirements"
      lead={`${t.requirements.length} found, ${flags} red flags. The buyer's words on the left, the agents' reading on the right.${readOnly ? "" : ` ${reviewedCount} reviewed.`}`}
      actions={
        <Segmented
          label="Show requirements"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "flags", label: `Red flags (${flags})` },
            { value: "clarify", label: "Not comply" },
            { value: "all", label: "All" },
          ]}
        />
      }
    >
      {!readOnly && (
        <label className={styles.reviewer}>
          <span>Reviewing as</span>
          <input
            className={ui.input}
            value={reviewer}
            maxLength={128}
            placeholder="Your name"
            onChange={(e) => setReviewer(e.target.value)}
            onBlur={() => reviewerName.set(reviewer.trim())}
          />
        </label>
      )}
      {review.isError && <ErrorState error={review.error} onRetry={() => review.reset()} />}
      {shown.length === 0 ? (
        <p className={styles.soft}>
          {filter === "flags" ? "No red flags in this tender." : "Every requirement is met as written."}
        </p>
      ) : (
        <ul className={styles.reqs}>
          <AnimatePresence initial={false} mode="popLayout">
            {shown.map((r) => (
              <RequirementRow
                key={r.id}
                r={r}
                review={reviews.get(r.id)}
                reviewer={reviewer}
                busy={review.isPending && review.variables?.rid === r.id}
                readOnly={readOnly}
                onReview={(verdict) => {
                  reviewerName.set(reviewer.trim());
                  review.mutate({ rid: r.id, verdict, reviewer: reviewer.trim() });
                }}
              />
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Section>
  );
}

function Norms({ t }: { t: TenderAnalysis }) {
  if (t.norms.length === 0) return null;
  return (
    <Section title="Norms and standards">
      <Table caption="Norms cited in the tender">
        <thead>
          <tr>
            <th>Norm</th>
            <th>Company</th>
            <th>Cited in</th>
          </tr>
        </thead>
        <tbody>
          {t.norms.map((n) => (
            <tr key={n.norm}>
              <td>{n.norm}</td>
              <td>
                <Tag tone={NORM_STATUS[n.status]?.tone ?? "quiet"}>
                  {NORM_STATUS[n.status]?.label ?? n.status}
                </Tag>
              </td>
              <td className={styles.soft}>{n.cited_in.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Section>
  );
}

/** One tender as the agents read it: the bid recommendation, every requirement with its source, the norms. */
export function TenderView({
  t,
  cid,
  readOnly = false,
  actions,
}: {
  t: TenderAnalysis;
  cid: string;
  readOnly?: boolean;
  actions?: ReactNode;
}) {
  const bid = BID[t.bid.decision];
  return (
    <div className={styles.view}>
      <header className={styles.head}>
        <p className={styles.soft}>
          {t.tender_id}. {t.buyer}. Due {date(t.due)}. {t.language === "de" ? "German" : "English"},{" "}
          {t.documents.join(", ")}.
        </p>
        <h2 className={styles.subject}>{t.subject}</h2>
      </header>
      <div className={styles.decision}>
        <div className={styles.decisionMain}>
          <Tag tone={bid.tone}>{bid.label}</Tag>
          <ul className={styles.reasons}>
            {[...t.bid.knockouts, ...t.bid.reasons, ...t.bid.conditions].map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
        <div className={styles.config}>
          <span className={styles.soft}>Configuration</span>
          <strong>{t.configuration.variant ?? "No variant fits"}</strong>
          <span className={styles.soft}>{t.configuration.reason}</span>
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      <Requirements t={t} cid={cid} readOnly={readOnly} />
      <Norms t={t} />
    </div>
  );
}
