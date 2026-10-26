import { date, days, eur, kpi, pct, value } from "../src/shared/lib/format";

describe("format", () => {
  it("writes numbers the same way everywhere", () => {
    expect(days(6.54)).toBe("6.5 days");
    expect(pct(0.9759, 1)).toBe("97.6 %");
    expect(eur(333501.4)).toBe("333,501 EUR");
    expect(days(null)).toBe("n/a");
  });

  it("reads dates without a time zone shifting the day", () => {
    expect(date("2026-08-03")).toBe("3 Aug 2026");
    expect(date(null)).toBe("not set");
  });

  it("writes requirement values as a buyer would read them", () => {
    expect(value(240, "kW")).toBe("240 kW");
    expect(value([-25, 40], "°C")).toBe("-25 to 40 °C");
    expect(value(true)).toBe("yes");
    expect(value(null)).toBe("no value");
  });

  it("formats KPIs by their kind", () => {
    expect(kpi(0.95, "percent")).toBe("95 %");
    expect(kpi(3.4, "days")).toBe("3.4 days");
    expect(kpi(null, "hours")).toBe("n/a");
  });
});
