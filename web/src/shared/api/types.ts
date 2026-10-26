/** The shapes the workbench API returns (src/rdw/api.py and src/rdw/service.py). */

export type Health = "green" | "amber" | "red";
export type KpiStatus = Health | "unknown";
export type Level = "automate" | "assist" | "not_yet" | "not_enough_evidence";
export type Verdict = "comply" | "clarify" | "deviate";
export type Stage = "discovery" | "pilot" | "scale" | string;
export type AgentId =
  | "requirement_extraction"
  | "red_flags"
  | "norms_report"
  | "bid_no_bid"
  | "configuration"
  | "technical_documentation";

export interface Problem {
  title: string;
  status: number;
  detail?: string;
}

export interface Agent {
  label: string;
  does: string;
  key_metric: string;
  activities: Record<string, { automate: number; assist: number }>;
}

export interface PortfolioCustomer {
  id: string;
  name: string;
  industry: string;
  stage: Stage;
  health: Health;
  renewal: string;
  readiness: Record<AgentId, Level>;
  scope: AgentId[];
  tenders_scored: number;
  value_per_year: number;
  next_step: string | null;
}

export interface Miss {
  tender: string;
  agent: AgentId;
  cause: string;
  owner: "platform" | "deployment";
  text: string;
  expected: unknown;
  got: unknown;
}

export interface BacklogItem {
  agent: AgentId;
  cause: string;
  kind: string;
  count: number;
  customers: string[];
  examples: string[];
  scales: boolean;
}

export interface Portfolio {
  customers: PortfolioCustomer[];
  platform_backlog: BacklogItem[];
  profile_fixes: (Miss & { customer: string })[];
  shared_kinds: string[];
  customer_specific_kinds: Record<string, string[]>;
  kind_labels: Record<string, string>;
  reviews: {
    acceptance: number | null;
    corrected_by_kind: { kind: string; confirmed: number; corrected: number; customers: string[] }[];
  };
  playbook: {
    days_kickoff_to_scored_pilot: number | null;
    days_kickoff_to_go_live: number | null;
    late_steps: { step: string; median_days_late: number; times: number }[];
  };
}

export interface Milestone {
  name: string;
  planned: string;
  done: string | null;
  state: "done" | "overdue" | "planned";
  days_late: number;
}

export interface Kpi {
  key: string;
  label: string;
  target: number;
  better: "higher" | "lower";
  format: "percent" | "days" | "hours" | "number";
  actual: number | null;
  baseline: number | null;
  basis: string;
  status: KpiStatus;
}

export interface NextStep {
  kind: string;
  who: string;
  text: string;
}

export interface Decision {
  date: string;
  decision: string;
  by: string;
  source: string;
}

export interface Deployment {
  customer: { id: string; name: string; industry: string; location: string };
  stage: Stage;
  kickoff: string;
  go_live: string | null;
  live: boolean;
  renewal: string;
  contract: { annual_fee: number; seats?: number };
  health: Health;
  scope: AgentId[];
  not_in_scope: Record<string, string>;
  stakeholders: { name: string; role: string; side: string; note: string }[];
  milestones: Milestone[];
  kpis: Kpi[];
  risks: { risk: string; owner: string; mitigation: string }[];
  decisions: Decision[];
  next_steps: NextStep[];
  summary: string;
}

export interface Activity {
  activity: string;
  role: string;
  count: number;
  share_of_cases: number;
  work_hours_mean: number;
  wait_hours_mean: number;
  wait_hours_per_case: number;
  waiting_kind: "queue" | "external";
}

export interface Discovery {
  cases: number;
  submitted: number;
  no_bid: number;
  period_days: number;
  lead_time_days: { median: number; p80: number };
  rework_share: number;
  activities: Activity[];
  bottleneck: { activity: string; kind: string; wait_hours_per_case: number } | null;
  internal_bottleneck: { activity: string; role: string; wait_hours_per_case: number } | null;
  utilisation: Record<string, number>;
  people: Record<string, number>;
  edges: { from: string; to: string; count: number }[];
  variants: { path: string[]; count: number }[];
  work_hours_by_role: Record<string, number>;
  busy_roles?: string[];
}

export interface TimelineRow {
  activity: string;
  before: { work: number; wait: number };
  after: { work: number; wait: number };
}

export interface LeadTime {
  before: number;
  after: number;
  saved_low: number;
  saved_high: number;
}

export interface WhatIf {
  factors: Record<string, number>;
  model_check: { observed_median_days: number; replayed_median_days: number };
  lead_time_days: LeadTime;
  timeline: TimelineRow[];
  hours_saved_by_role: Record<string, number>;
  hours_saved: number;
  period_days: number;
}

export interface Assumptions {
  hourly_cost: Record<string, number>;
  hours_per_person_year: number;
  annual_fee: number;
  volume_growth: number;
}

export interface ValueCase {
  assumptions: Assumptions;
  by_role: { role: string; hours: number; rate: number; value: number; people: number }[];
  hours_per_year: number;
  capacity_people: number;
  gross_per_year: number;
  net_per_year: number;
  payback_months: number | null;
  lead_time_days: LeadTime;
  statement: string;
  what_if: WhatIf;
}

export interface ReadinessRow {
  label: string;
  does: string;
  metric: string;
  right: number;
  of: number;
  rate: number;
  lower_bound: number;
  level: Level;
  misses: number;
  fix_in_platform: number;
  fix_in_deployment: number;
}

export interface Metric {
  right: number;
  of: number;
  rate: number;
  lower_bound: number;
}

export interface Readiness {
  customer: string;
  tenders: number;
  metrics: Record<string, Metric>;
  readiness: Record<AgentId, ReadinessRow>;
  misses: Miss[];
  bar: { confidence: number; automate: number; assist: number; min_items: number };
  kind_labels: Record<string, string>;
}

export interface LiveComparison {
  since: string;
  discovery: Discovery;
  activities: {
    activity: string;
    hours_before: number;
    hours_after: number;
    actual_factor: number;
    projected_factor: number;
    gap: number;
    status: "no_agent" | "behind" | "on_plan";
  }[];
  projected: WhatIf;
}

export interface TenderRow {
  id: string;
  subject: string;
  buyer: string;
  due: string | null;
  language: "de" | "en";
  decision: BidDecision;
  variant: string | null;
  requirements: number;
  red_flags: number;
  knockouts: number;
  reviewed: number;
}

export type BidDecision = "bid" | "bid_with_conditions" | "no_bid";

export interface Requirement {
  id: string;
  source: { doc: string; file: string; locator: string; text: string };
  kind: string;
  label: string;
  value: unknown;
  unit: string | null;
  priority: "mandatory" | "desirable" | "informative";
  norms: string[];
  verdict: Verdict;
  reason: string;
  red_flag: boolean;
  severity: "knockout" | "major" | "minor" | null;
  confidence: number;
}

export interface Review {
  customer: string;
  tender: string;
  requirement: string;
  kind: string;
  action: "confirm" | "correct";
  agent_verdict: Verdict;
  verdict: Verdict;
  comment: string;
  reviewer: string;
  at: string;
}

export interface TenderAnalysis {
  tender_id: string;
  customer: string;
  language: "de" | "en";
  subject: string;
  buyer: string;
  due: string | null;
  documents: string[];
  requirements: Requirement[];
  norms: { norm: string; status: "certified" | "not_certified" | "unknown"; cited_in: string[] }[];
  bid: { decision: BidDecision; reasons: string[]; knockouts: string[]; conditions: string[] };
  configuration: { variant: string | null; reason: string };
  reviews?: Review[];
}

export interface SteerCo {
  customer: string;
  date: string;
  health: Health;
  markdown: string;
  asks: NextStep[];
}
