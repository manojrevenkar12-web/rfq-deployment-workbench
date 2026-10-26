/** Words and tones for the states the API reports, so every screen names them the same way. */
import type { BidDecision, Health, KpiStatus, Level, Verdict } from "../api/types";

export type Tone = "good" | "watch" | "bad" | "info" | "quiet";

export const HEALTH: Record<Health, { label: string; tone: Tone }> = {
  green: { label: "On track", tone: "good" },
  amber: { label: "Needs attention", tone: "watch" },
  red: { label: "At risk", tone: "bad" },
};

export const KPI_STATUS: Record<KpiStatus, Tone> = {
  green: "good",
  amber: "watch",
  red: "bad",
  unknown: "quiet",
};

export const LEVEL: Record<Level, { label: string; tone: Tone; long: string }> = {
  automate: {
    label: "Works on its own",
    tone: "good",
    long: "The lower bound clears the bar to run without a person checking every answer.",
  },
  assist: {
    label: "Assists a person",
    tone: "info",
    long: "Good enough to draft; a person confirms each answer.",
  },
  not_yet: { label: "Not yet", tone: "bad", long: "Below the bar to assist: fix the misses first." },
  not_enough_evidence: {
    label: "Too few tenders",
    tone: "quiet",
    long: "Fewer scored items than the minimum: score more past tenders.",
  },
};

export const VERDICT: Record<Verdict, { label: string; tone: Tone }> = {
  comply: { label: "Comply", tone: "good" },
  clarify: { label: "Clarify", tone: "watch" },
  deviate: { label: "Deviation", tone: "bad" },
};

export const BID: Record<BidDecision, { label: string; tone: Tone }> = {
  bid: { label: "Bid", tone: "good" },
  bid_with_conditions: { label: "Bid with conditions", tone: "watch" },
  no_bid: { label: "No bid", tone: "bad" },
};

export const STAGE: Record<string, string> = {
  discovery: "Discovery",
  pilot: "Pilot",
  scale: "Live",
};

export const NORM_STATUS: Record<string, { label: string; tone: Tone }> = {
  certified: { label: "Certified", tone: "good" },
  not_certified: { label: "Not certified", tone: "bad" },
  unknown: { label: "Not in the profile", tone: "watch" },
};

/** Motion, mirrored from tokens.css (--duration-move, --ease-out) for Framer Motion, which needs numbers. */
export const MOTION = {
  move: 0.42,
  draw: 0.7,
  quick: 0.14,
  ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number],
} as const;

/** The agents in the order a tender passes through them. */
export const AGENT_ORDER = [
  "requirement_extraction",
  "red_flags",
  "norms_report",
  "bid_no_bid",
  "configuration",
  "technical_documentation",
] as const;

export const AGENT_SHORT: Record<(typeof AGENT_ORDER)[number], string> = {
  requirement_extraction: "Requirements",
  red_flags: "Red flags",
  norms_report: "Norms",
  bid_no_bid: "Bid / no-bid",
  configuration: "Configuration",
  technical_documentation: "Documentation",
};
