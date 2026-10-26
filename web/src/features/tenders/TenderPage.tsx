import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { MOTION } from "../../shared/theme/tokens";
import { Button, ErrorState, QueryView, SkeletonBlock } from "../../shared/ui";
import { useCid } from "../customer/CustomerLayout";
import { downloadMatrix, useLetter, useTender } from "./api";
import styles from "./Tender.module.css";
import { TenderView } from "./TenderView";

function Downloads({ cid, tid }: { cid: string; tid: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [letterOpen, setLetterOpen] = useState(false);
  const letter = useLetter(cid, tid, letterOpen);
  const fetchMatrix = async () => {
    setBusy(true);
    setError(null);
    try {
      await downloadMatrix(cid, tid);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button variant="primary" busy={busy} onClick={() => void fetchMatrix()}>
        Download compliance matrix
      </Button>
      <Button onClick={() => setLetterOpen((o) => !o)} aria-expanded={letterOpen} aria-controls="letter">
        {letterOpen ? "Hide clarification letter" : "Show clarification letter"}
      </Button>
      {error != null && <ErrorState error={error} onRetry={() => void fetchMatrix()} />}
      <AnimatePresence initial={false}>
        {letterOpen && (
          <motion.div
            id="letter"
            key="letter"
            className={styles.letterWrap}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: MOTION.move, ease: MOTION.ease }}
          >
            <QueryView
              query={letter}
              skeleton={<SkeletonBlock label="Writing the letter" rows={4} height="var(--space-5)" />}
            >
              {(text) => (
                <>
                  <pre className={styles.letter}>{text}</pre>
                  <Button variant="quiet" onClick={() => void navigator.clipboard?.writeText(text)}>
                    Copy letter
                  </Button>
                </>
              )}
            </QueryView>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export function TenderPage() {
  const cid = useCid();
  const { tid = "" } = useParams();
  const q = useTender(cid, tid);
  return (
    <>
      <p>
        <Link to={`/c/${cid}/tenders`}>All tenders</Link>
      </p>
      <QueryView
        query={q}
        skeleton={<SkeletonBlock label="Reading the tender" rows={6} height="var(--space-8)" />}
      >
        {(t) => <TenderView t={t} cid={cid} actions={<Downloads cid={cid} tid={tid} />} />}
      </QueryView>
    </>
  );
}
