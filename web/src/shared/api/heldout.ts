import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type { AgentId, Level, Metric } from "./types";

export interface HeldoutSet {
  set: string;
  status: string;
  run_at: string;
  customers: Record<
    string,
    {
      tenders: number;
      metrics: Record<string, Metric>;
      readiness: Record<AgentId, Level>;
      misses: { agent: AgentId; cause: string; owner: "platform" | "deployment"; count: number }[];
    }
  >;
}

export const useHeldout = () =>
  useQuery({
    queryKey: ["heldout"],
    queryFn: () => api.get<HeldoutSet[]>("/api/heldout"),
    staleTime: Infinity,
  });
