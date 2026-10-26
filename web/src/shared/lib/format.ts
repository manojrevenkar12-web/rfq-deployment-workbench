/** Formatting in one place, so a number reads the same on every screen. */

const LOCALE = "en-GB";

export const days = (d: number | null | undefined, digits = 1) =>
  d == null
    ? "n/a"
    : `${d.toLocaleString(LOCALE, { maximumFractionDigits: digits, minimumFractionDigits: digits })} days`;

export const hours = (h: number | null | undefined, digits = 0) =>
  h == null ? "n/a" : `${h.toLocaleString(LOCALE, { maximumFractionDigits: digits })} h`;

export const pct = (x: number | null | undefined, digits = 0) =>
  x == null
    ? "n/a"
    : `${(x * 100).toLocaleString(LOCALE, { maximumFractionDigits: digits, minimumFractionDigits: digits })} %`;

export const eur = (x: number | null | undefined) =>
  x == null ? "n/a" : `${Math.round(x).toLocaleString(LOCALE)} EUR`;

export const int = (x: number | null | undefined) =>
  x == null ? "n/a" : Math.round(x).toLocaleString(LOCALE);

export const people = (x: number) => `${x.toLocaleString(LOCALE, { maximumFractionDigits: 1 })} people`;

export function date(iso: string | null | undefined): string {
  if (!iso) return "not set";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00Z`);
  return d.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

const ROLE: Record<string, string> = {
  sales: "Sales",
  sales_engineering: "Sales engineering",
  engineering: "Engineering",
  quality: "Quality",
  legal: "Legal",
  management: "Management",
  buyer: "Buyer",
};

export const role = (r: string) => ROLE[r] ?? humanise(r);

export const humanise = (s: string) => {
  const t = s.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

/** A requirement's value as the buyer would read it. */
export function value(v: unknown, unit?: string | null): string {
  if (v == null) return "no value";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return `${v.map((x) => value(x)).join(" to ")}${unit ? ` ${unit}` : ""}`;
  if (typeof v === "number") return `${v.toLocaleString(LOCALE)}${unit ? ` ${unit}` : ""}`;
  if (typeof v === "object") return JSON.stringify(v);
  return `${String(v)}${unit ? ` ${unit}` : ""}`;
}

export function kpi(x: number | null, format: string): string {
  if (x == null) return "n/a";
  if (format === "percent") return pct(x);
  if (format === "days") return days(x);
  if (format === "hours") return hours(x, 1);
  return x.toLocaleString(LOCALE, { maximumFractionDigits: 2 });
}
