import { AnimatePresence, motion } from "framer-motion";
import { type ChangeEvent, type DragEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";

import type { BidDecision, TenderRow } from "../../shared/api/types";
import { date } from "../../shared/lib/format";
import { BID, MOTION } from "../../shared/theme/tokens";
import {
  Button,
  EmptyState,
  ErrorState,
  QueryView,
  Section,
  SkeletonBlock,
  Table,
  Tag,
  ui,
} from "../../shared/ui";
import { Segmented } from "../../shared/ui/Segmented";
import { useCid } from "../customer/CustomerLayout";
import { useInbox, useTenders } from "./api";
import styles from "./Tenders.module.css";
import { TenderView } from "./TenderView";

type DecisionFilter = "all" | BidDecision;

const ACCEPT = ".pdf,.xlsx,.eml,.txt,.md";

function Inbox({ cid }: { cid: string }) {
  const inbox = useInbox(cid);
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const send = (files: FileList | null) => {
    if (files && files.length > 0) inbox.mutate(Array.from(files));
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    send(e.dataTransfer.files);
  };
  return (
    <Section
      title="Read a new tender"
      lead="Drop the documents of one tender: the specification (PDF), the bill of quantities (Excel), the buyer's e-mail. Nothing is added to the scored history."
    >
      <div
        className={styles.drop}
        data-over={over}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <p>Drop files here, or</p>
        <Button variant="primary" busy={inbox.isPending} onClick={() => input.current?.click()}>
          Choose files
        </Button>
        <input
          ref={input}
          className="visually-hidden"
          type="file"
          multiple
          accept={ACCEPT}
          aria-label="Tender documents"
          onChange={(e: ChangeEvent<HTMLInputElement>) => {
            send(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {inbox.isError && <ErrorState error={inbox.error} onRetry={() => inbox.reset()} />}
      <AnimatePresence>
        {inbox.data && (
          <motion.div
            key={inbox.data.tender_id}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: MOTION.move, ease: MOTION.ease }}
            className={styles.result}
          >
            <TenderView
              t={inbox.data}
              cid={cid}
              readOnly
              actions={
                <Button variant="quiet" onClick={() => inbox.reset()}>
                  Close this tender
                </Button>
              }
            />
          </motion.div>
        )}
      </AnimatePresence>
    </Section>
  );
}

function matches(t: TenderRow, decision: DecisionFilter, text: string) {
  if (decision !== "all" && t.decision !== decision) return false;
  const s = text.trim().toLowerCase();
  return !s || `${t.id} ${t.subject} ${t.buyer}`.toLowerCase().includes(s);
}

function List({ cid, rows }: { cid: string; rows: TenderRow[] }) {
  const [decision, setDecision] = useState<DecisionFilter>("all");
  const [text, setText] = useState("");
  const shown = rows.filter((t) => matches(t, decision, text));
  const count = (d: BidDecision) => rows.filter((t) => t.decision === d).length;
  return (
    <Section
      title="Past tenders"
      lead={`${rows.length} tenders the agents were scored on against the customer's own compliance matrices and bid decisions.`}
    >
      <div className={styles.filters}>
        <Segmented
          label="Filter by recommendation"
          value={decision}
          onChange={setDecision}
          options={[
            { value: "all", label: "All" },
            { value: "bid", label: `Bid (${count("bid")})` },
            { value: "bid_with_conditions", label: `With conditions (${count("bid_with_conditions")})` },
            { value: "no_bid", label: `No bid (${count("no_bid")})` },
          ]}
        />
        <label className={styles.search}>
          <span className="visually-hidden">Search tenders</span>
          <input
            className={ui.input}
            type="search"
            placeholder="Search subject, buyer or number"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
      </div>
      {shown.length === 0 ? (
        <EmptyState
          title="No tender matches"
          action={
            <Button
              onClick={() => {
                setDecision("all");
                setText("");
              }}
            >
              Show all tenders
            </Button>
          }
        >
          Nothing fits this recommendation and search.
        </EmptyState>
      ) : (
        <Table caption="Tenders">
          <thead>
            <tr>
              <th>Tender</th>
              <th>Due</th>
              <th>Recommendation</th>
              <th>Variant</th>
              <th className={ui.num}>Requirements</th>
              <th className={ui.num}>Red flags</th>
              <th className={ui.num}>Reviewed</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => (
              <tr key={t.id}>
                <td>
                  <Link to={`/c/${cid}/tenders/${t.id}`} className={styles.subject}>
                    {t.subject}
                  </Link>
                  <span className={styles.sub}>
                    {t.id}, {t.buyer}
                  </span>
                </td>
                <td className={styles.nowrap}>{date(t.due)}</td>
                <td>
                  <Tag tone={BID[t.decision].tone}>{BID[t.decision].label}</Tag>
                </td>
                <td>{t.variant ?? "none"}</td>
                <td className={ui.num}>{t.requirements}</td>
                <td className={ui.num}>{t.red_flags}</td>
                <td className={ui.num}>{t.reviewed ? `${t.reviewed} of ${t.requirements}` : ""}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Section>
  );
}

export function TendersPage() {
  const cid = useCid();
  const q = useTenders(cid);
  return (
    <>
      <Inbox cid={cid} />
      <QueryView
        query={q}
        skeleton={<SkeletonBlock label="Reading the tenders" rows={8} height="var(--space-6)" />}
        isEmpty={(rows) => rows.length === 0}
        empty={
          <EmptyState title="No past tenders yet">
            Ask the customer for twenty or more past tenders with the compliance matrix and bid decision they
            sent; put them in data/customers/{cid}/tenders/. Without them the agents cannot be scored.
          </EmptyState>
        }
      >
        {(rows) => <List cid={cid} rows={rows} />}
      </QueryView>
    </>
  );
}
