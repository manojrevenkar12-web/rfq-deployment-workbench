import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { usePortfolio } from "../features/portfolio/api";
import { Skeleton } from "../shared/ui";
import { HEALTH, STAGE } from "../shared/theme/tokens";
import styles from "./Shell.module.css";

function CustomerLinks() {
  const q = usePortfolio();
  const { pathname } = useLocation();
  if (q.isPending)
    return (
      <>
        {[0, 1, 2].map((i) => (
          <li key={i} aria-hidden>
            <Skeleton height="var(--space-7)" width="var(--rail-width)" />
          </li>
        ))}
      </>
    );
  if (q.isError || !q.data) return null; // the page itself shows the error and the retry
  return (
    <>
      {q.data.customers.map((c) => {
        const to = `/c/${c.id}`;
        const within = pathname.startsWith(`${to}/`);
        return (
          <li key={c.id}>
            <NavLink to={to} end className={`${styles.link} ${within ? styles.within : ""}`}>
              <span className={`${styles.health} ${styles[c.health]}`} title={HEALTH[c.health].label} />
              <span className={styles.linkName}>{c.name}</span>
              <span className={styles.linkMeta}>
                {STAGE[c.stage] ?? c.stage}, {HEALTH[c.health].label.toLowerCase()}
              </span>
            </NavLink>
          </li>
        );
      })}
    </>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <aside className={styles.rail}>
        <Link to="/" className={styles.brand}>
          <strong>RFQ Deployment Workbench</strong>
          <span>For the people who put the agents to work</span>
        </Link>
        <nav aria-label="Customers">
          <ul className={styles.nav}>
            <li>
              <NavLink to="/" end className={styles.link}>
                <span className={`${styles.health} ${styles.portfolioMark}`} aria-hidden />
                <span className={styles.linkName}>All customers</span>
              </NavLink>
            </li>
            <li className={styles.navHeading} aria-hidden>
              Deployments
            </li>
            <CustomerLinks />
          </ul>
        </nav>
        <p className={styles.railNote}>
          Customers, tenders and processes are simulated; nothing here is a real company.
        </p>
      </aside>
      <main id="main" className={styles.main}>
        {children}
      </main>
    </div>
  );
}
