import { motion } from "framer-motion";
import { NavLink, Outlet, useLocation, useParams } from "react-router-dom";

import { date } from "../../shared/lib/format";
import { HEALTH, MOTION, STAGE } from "../../shared/theme/tokens";
import { ErrorState, Skeleton, Tag } from "../../shared/ui";
import { useDeployment } from "./api";
import styles from "./Customer.module.css";

const TABS = [
  { to: "", label: "Overview" },
  { to: "process", label: "Process" },
  { to: "tenders", label: "Tenders" },
  { to: "readiness", label: "Readiness" },
  { to: "value", label: "Value case" },
] as const;

export function useCid(): string {
  const { cid } = useParams();
  return cid ?? "";
}

function Tabs({ cid }: { cid: string }) {
  const { pathname } = useLocation();
  const base = `/c/${cid}`;
  const active = (to: string) =>
    to === "" ? pathname === base || pathname === `${base}/` : pathname.startsWith(`${base}/${to}`);
  return (
    <nav className={styles.tabs} aria-label="Customer views">
      <ul>
        {TABS.map((t) => (
          <li key={t.to}>
            <NavLink to={t.to ? `${base}/${t.to}` : base} end={t.to === ""} className={styles.tab}>
              {t.label}
              {active(t.to) && (
                <motion.span
                  layoutId="tab-underline"
                  className={styles.underline}
                  transition={{ duration: MOTION.move, ease: MOTION.ease }}
                />
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function CustomerLayout() {
  const cid = useCid();
  const q = useDeployment(cid);

  if (q.isError && !q.data) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;

  const d = q.data;
  return (
    <>
      <header className={styles.header}>
        {d ? (
          <>
            <h1 className={styles.name}>{d.customer.name}</h1>
            <div className={styles.meta}>
              <Tag tone={HEALTH[d.health].tone}>{HEALTH[d.health].label}</Tag>
              <span>
                {d.customer.industry}, {d.customer.location}.
              </span>
              <span>
                {STAGE[d.stage] ?? d.stage}
                {d.live
                  ? ` since ${date(d.go_live)}`
                  : d.go_live
                    ? `, go-live planned ${date(d.go_live)}`
                    : `, kicked off ${date(d.kickoff)}`}
                . Renewal {date(d.renewal)}.
              </span>
            </div>
          </>
        ) : (
          <div role="status" aria-label="Loading the customer" className={styles.loading}>
            <Skeleton height="var(--text-4xl)" width="70%" />
            <Skeleton height="var(--space-5)" width="45%" />
          </div>
        )}
      </header>
      <Tabs cid={cid} />
      <div className={styles.body}>
        <Outlet />
      </div>
    </>
  );
}
