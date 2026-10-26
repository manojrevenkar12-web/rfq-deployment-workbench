/** Responses captured from the real API (`rdw serve` on the simulated customers, RDW_TODAY=2026-10-26). */
import discovery from "./fixtures/discovery.json";
import gleiswerk from "./fixtures/gleiswerk.json";
import heldout from "./fixtures/heldout.json";
import live from "./fixtures/live.json";
import portfolio from "./fixtures/portfolio.json";
import readiness from "./fixtures/readiness.json";
import steerco from "./fixtures/steerco.json";
import tender from "./fixtures/tender.json";
import tenders from "./fixtures/tenders.json";
import value from "./fixtures/value.json";
import voltaro from "./fixtures/voltaro.json";
import type { Routes } from "./harness";

export const fx = {
  discovery,
  gleiswerk,
  heldout,
  live,
  portfolio,
  readiness,
  steerco,
  tender,
  tenders,
  value,
  voltaro,
};

/** Everything the voltaro screens ask for. */
export function voltaroRoutes(): Routes {
  return {
    "GET /api/portfolio": portfolio,
    "GET /api/heldout": heldout,
    "GET /api/customers/voltaro": voltaro,
    "GET /api/customers/voltaro/discovery": discovery,
    "GET /api/customers/voltaro/live": live,
    "POST /api/customers/voltaro/value": value,
    "GET /api/customers/voltaro/readiness": readiness,
    "GET /api/customers/voltaro/tenders": tenders,
    "GET /api/customers/voltaro/tenders/VO-2026-001": tender,
    "GET /api/customers/voltaro/steerco": steerco,
  };
}
