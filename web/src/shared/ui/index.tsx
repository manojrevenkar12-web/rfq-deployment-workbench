import type { UseQueryResult } from "@tanstack/react-query";
import { type ButtonHTMLAttributes, type FormEvent, type ReactNode, useState } from "react";

import { ApiError, token } from "../api/client";
import type { Tone } from "../theme/tokens";
import styles from "./ui.module.css";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

const toneClass = (tone: Tone) => (tone === "quiet" ? styles.quietTone : styles[tone]);

export function Button({
  variant = "default",
  busy,
  children,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "quiet"; busy?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      className={cx(styles.button, variant !== "default" && styles[variant], className)}
      disabled={busy || rest.disabled}
      aria-busy={busy || undefined}
    >
      {busy && <span className={styles.spinner} aria-hidden />}
      {children}
    </button>
  );
}

export function Skeleton({ height = "var(--space-4)", width = "100%" }: { height?: string; width?: string }) {
  return <div className={styles.skeleton} style={{ height, width }} aria-hidden />;
}

/** A labelled loading placeholder shaped like the content it stands in for. */
export function SkeletonBlock({
  label,
  rows = 5,
  height = "var(--space-7)",
}: {
  label: string;
  rows?: number;
  height?: string;
}) {
  return (
    <div className={styles.skeletons} role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={height} width={i === rows - 1 ? "62%" : "100%"} />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className={styles.state} aria-live="polite">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </section>
  );
}

function TokenForm({ onDone }: { onDone: () => void }) {
  const [value, setValue] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    token.set(value);
    onDone();
  };
  return (
    <form className={styles.tokenForm} onSubmit={submit}>
      <label className="visually-hidden" htmlFor="api-token">
        API token
      </label>
      <input
        id="api-token"
        className={styles.input}
        type="password"
        autoComplete="off"
        placeholder="Paste the API token"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <Button type="submit" variant="primary" disabled={!value.trim()}>
        Use token
      </Button>
    </form>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const e = error instanceof ApiError ? error : null;
  return (
    <section className={cx(styles.state, styles.error)} role="alert">
      <h2>{e?.title ?? "This view could not load"}</h2>
      <p>
        {e?.needsToken
          ? "This workbench runs with RDW_API_TOKEN set. Paste the token to continue; it is kept for this tab only."
          : (e?.detail ?? (error instanceof Error ? error.message : "Something went wrong while loading."))}
      </p>
      {e?.needsToken ? <TokenForm onDone={onRetry} /> : <Button onClick={onRetry}>Try again</Button>}
    </section>
  );
}

/**
 * The three states every view has before it shows data: loading (a skeleton shaped like the view), failed
 * (what happened and a retry), empty (what it means and what to do next). Data already shown stays while it
 * refreshes.
 */
export function QueryView<T>({
  query,
  skeleton,
  isEmpty,
  empty,
  children,
}: {
  query: UseQueryResult<T>;
  skeleton: ReactNode;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) return <>{skeleton}</>;
  if (query.isError && query.data === undefined)
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const data = query.data as T;
  if (isEmpty?.(data)) return <>{empty}</>;
  return <>{children(data)}</>;
}

export function Tag({ tone, children, title }: { tone: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={cx(styles.tag, toneClass(tone))} title={title}>
      <span className={styles.swatch} aria-hidden />
      {children}
    </span>
  );
}

export function PageHeader({
  title,
  lead,
  actions,
}: {
  title: ReactNode;
  lead?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className={styles.header}>
      <div>
        <h1>{title}</h1>
        {lead && <p>{lead}</p>}
      </div>
      {actions}
    </header>
  );
}

export function Section({
  title,
  lead,
  actions,
  panel,
  children,
  id,
}: {
  title: string;
  lead?: ReactNode;
  actions?: ReactNode;
  panel?: boolean;
  children: ReactNode;
  id?: string;
}) {
  const headingId = id ?? `s-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <section className={cx(styles.section, panel && styles.panel)} aria-labelledby={headingId}>
      <div className={styles.sectionHead}>
        <h2 id={headingId}>{title}</h2>
        {actions}
      </div>
      {lead && <p className={styles.lead}>{lead}</p>}
      {children}
    </section>
  );
}

export function Figure({ value, label, compact }: { value: ReactNode; label: ReactNode; compact?: boolean }) {
  return (
    <div className={cx(styles.figure, compact && styles.compact)}>
      <span className={styles.figureValue}>{value}</span>
      <span className={styles.figureLabel}>{label}</span>
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <p className={styles.notice} role="status">
      {children}
    </p>
  );
}

/** The lower bound an agent is judged on, its plain rate as a tick, and the two bars it has to clear. */
export function ReadinessMeter({
  lowerBound,
  rate,
  tone,
  marks,
  label,
}: {
  lowerBound: number;
  rate: number;
  tone: Tone;
  marks: number[];
  label: string;
}) {
  return (
    <div
      className={cx(styles.meter, toneClass(tone))}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={lowerBound}
      aria-valuetext={`lower bound ${Math.round(lowerBound * 100)} %, measured ${Math.round(rate * 100)} %`}
    >
      <span className={styles.meterFill} style={{ width: `${lowerBound * 100}%` }} />
      {marks.map((m) => (
        <span key={m} className={styles.meterMark} style={{ left: `${m * 100}%` }} aria-hidden />
      ))}
      <span className={styles.meterRate} style={{ left: `calc(${rate * 100}% - 1px)` }} aria-hidden />
    </div>
  );
}

export function Table({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className={styles.tableWrap} role="region" aria-label={caption} tabIndex={0}>
      <table>
        <caption className="visually-hidden">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export const ui = { num: styles.num, quote: styles.quote, input: styles.input, panel: styles.panel };
